from __future__ import annotations

import logging
from collections import Counter

from .diff_parser import DiffParser
from .formatter import format_review_summary
from .llm_client import GeminiClient, InvalidLLMResponseError, LLMResponseParser
from .models import Finding, ReviewResult, ReviewSummary
from .security import SecurityAnalyzer
from .severity import Severity, classify_severity

logger = logging.getLogger(__name__)


class ReviewEngine:
    def __init__(
        self,
        llm_client: GeminiClient | None = None,
        security_analyzer: SecurityAnalyzer | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.security_analyzer = security_analyzer or SecurityAnalyzer()

    def analyze_diff(self, diff_text: str, file_paths: list[str] | None = None) -> ReviewResult:
        file_paths = file_paths or []
        if not diff_text or not diff_text.strip():
            return ReviewResult(findings=[], summary="No diff to review.", metadata={"empty_pr": True})

        entries = DiffParser.parse(diff_text)
        relevant_paths = DiffParser.filter_irrelevant_files([entry.file_path for entry in entries] + file_paths)
        findings: list[Finding] = []

        for entry in entries:
            if entry.file_path and entry.file_path not in relevant_paths:
                continue
            content = entry.text
            findings.extend(self.security_analyzer.scan_text(content))

        if self.llm_client is not None:
            prompt = self._build_prompt(diff_text, relevant_paths)
            try:
                payload = self.llm_client.generate(prompt)
                parsed = LLMResponseParser.parse(payload)
                findings.extend(parsed.findings)
            except InvalidLLMResponseError as exc:
                logger.warning(
                    "LLM response invalid: %s. Continuing review without LLM findings.",
                    exc,
                )

        deduped = self._dedupe_findings(findings)
        summary = self._build_summary(deduped)
        return ReviewResult(findings=deduped, summary=format_review_summary(summary), metadata={
            "empty_pr": False,
            "files_analyzed": relevant_paths,
            "finding_count": len(deduped),
        })

    def _build_prompt(self, diff_text: str, file_paths: list[str]) -> str:
        trimmed = diff_text[:60000]
        return (
            "Review this pull request diff and return strict JSON with keys 'findings' and 'summary'. "
            f"Files considered: {file_paths or 'none'}.\n\n{trimmed}"
        )

    def _dedupe_findings(self, findings: list[Finding]) -> list[Finding]:
        seen: set[tuple[str, int, str, str, str, str]] = set()
        deduped: list[Finding] = []
        for finding in findings:
            signature = finding.signature
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(finding)
        return deduped

    def _build_summary(self, findings: list[Finding]) -> ReviewSummary:
        severity_counts = Counter(finding.severity for finding in findings)
        category_counts = Counter(finding.category for finding in findings)

        top = [finding.title for finding in findings[:5] if finding.title]
        overall = "PASS"
        if any(classify_severity(finding.severity) in {Severity.CRITICAL, Severity.HIGH} for finding in findings):
            overall = "NEEDS_CHANGES"
        elif findings:
            overall = "REVIEW"

        recommendation = "No action needed." if not findings else "Address HIGH and CRITICAL findings before merging."
        return ReviewSummary(
            overall=overall,
            total_findings=len(findings),
            severity_counts={
                level: severity_counts.get(level, 0)
                for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
            },
            category_counts=dict(category_counts),
            top_issues=top,
            recommendation=recommendation,
        )
