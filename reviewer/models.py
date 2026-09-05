from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Finding:
    file: str = ""
    line: int = 0
    severity: str = "INFO"
    category: str = "CODE_QUALITY"
    title: str = ""
    description: str = ""
    recommendation: str = ""
    confidence: float = 0.0

    @property
    def signature(self) -> tuple[str, int, str, str, str, str]:
        return (
            self.file,
            self.line,
            self.severity,
            self.category,
            self.title,
            self.description,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Finding":
        if not isinstance(payload, dict):
            raise ValueError("Finding payload must be a dictionary")
        return cls(
            file=str(payload.get("file", "")),
            line=int(payload.get("line", 0) or 0),
            severity=str(payload.get("severity", "INFO")).upper(),
            category=str(payload.get("category", "CODE_QUALITY")).upper(),
            title=str(payload.get("title", "Review finding")),
            description=str(payload.get("description", "")),
            recommendation=str(payload.get("recommendation", "")),
            confidence=float(payload.get("confidence", 0.0) or 0.0),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
        }


@dataclass
class ReviewSummary:
    overall: str = "PASS"
    total_findings: int = 0
    severity_counts: dict[str, int] = field(default_factory=dict)
    category_counts: dict[str, int] = field(default_factory=dict)
    top_issues: list[str] = field(default_factory=list)
    recommendation: str = "No action needed."

    def as_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "total_findings": self.total_findings,
            "severity_counts": self.severity_counts,
            "category_counts": self.category_counts,
            "top_issues": self.top_issues,
            "recommendation": self.recommendation,
        }


@dataclass
class ReviewResult:
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "findings": [finding.as_dict() for finding in self.findings],
            "summary": self.summary,
            "metadata": self.metadata,
        }


@dataclass
class DiffHunk:
    header: str = ""
    content: str = ""


@dataclass
class DiffEntry:
    file_path: str = ""
    status: str = "modified"
    hunks: list[DiffHunk] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(hunk.content for hunk in self.hunks)
