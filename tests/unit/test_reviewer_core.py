from __future__ import annotations

import pytest

from reviewer.diff_parser import DiffParser
from reviewer.formatter import format_review_summary
from reviewer.github_client import AuthenticationError, GitHubAPIError, GitHubClient, RateLimitError
from reviewer.llm_client import InvalidLLMResponseError, LLMResponseParser
from reviewer.models import Finding, ReviewSummary
from reviewer.security import SecurityAnalyzer
from reviewer.severity import Severity, classify_severity


def test_diff_parser_extracts_hunks_and_files():
    diff = """diff --git a/app.py b/app.py
index 1111111..2222222 100644
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
 def demo():
+    token = \"abc123\"
     return 1
+    return 2
"""
    parser = DiffParser()
    entries = parser.parse(diff)

    assert len(entries) == 1
    assert entries[0].file_path == "app.py"
    assert entries[0].hunks
    assert "token" in entries[0].hunks[0].content


def test_generated_files_are_filtered_out():
    paths = [
        "src/app.py",
        "dist/bundle.js",
        "package-lock.json",
        "node_modules/pkg/index.js",
        "coverage.xml",
        "README.md",
    ]

    filtered = DiffParser.filter_irrelevant_files(paths)

    assert filtered == ["src/app.py", "README.md"]


def test_security_analyzer_detects_issues():
    analyzer = SecurityAnalyzer()
    result = analyzer.scan_text(
        """
        password = \"hardcoded-pass\"
        query = \"SELECT * FROM users WHERE id = %s\" % user_input
        subprocess.run(cmd, shell=True)
        """
    )

    assert any(item.category == "SECURITY" for item in result)
    assert any(item.title.lower().startswith("hardcoded") for item in result)


def test_severity_classification_levels():
    assert classify_severity("critical") == Severity.CRITICAL
    assert classify_severity("HIGH") == Severity.HIGH
    assert classify_severity("medium") == Severity.MEDIUM
    assert classify_severity("info") == Severity.INFO


def test_llm_response_parser_handles_valid_response():
    payload = {
        "findings": [
            {
                "file": "src/a.py",
                "line": 14,
                "severity": "HIGH",
                "category": "SECURITY",
                "title": "Hardcoded secret",
                "description": "Secret detected.",
                "recommendation": "Move to env var.",
                "confidence": 0.91,
            }
        ],
        "summary": "Needs cleanup",
    }

    parsed = LLMResponseParser.parse(payload)

    assert len(parsed.findings) == 1
    assert parsed.findings[0].file == "src/a.py"
    assert parsed.summary == "Needs cleanup"


def test_invalid_llm_response_raises():
    with pytest.raises(InvalidLLMResponseError):
        LLMResponseParser.parse({"bad": "data"})


def test_duplicate_finding_detection():
    findings = [
        Finding(
            file="src/app.py",
            line=10,
            severity="HIGH",
            category="SECURITY",
            title="Hardcoded secret",
            description="x",
            recommendation="y",
            confidence=0.8,
        ),
        Finding(
            file="src/app.py",
            line=10,
            severity="HIGH",
            category="SECURITY",
            title="Hardcoded secret",
            description="x",
            recommendation="y",
            confidence=0.8,
        ),
        Finding(
            file="src/other.py",
            line=20,
            severity="LOW",
            category="QUALITY",
            title="Refactor",
            description="x",
            recommendation="y",
            confidence=0.6,
        ),
    ]

    deduped = list(dict.fromkeys([f.signature for f in findings]))

    assert len(deduped) == 2


def test_empty_pr_handling():
    summary = ReviewSummary(
        total_findings=0,
        severity_counts={"LOW": 0},
        category_counts={},
        top_issues=[],
        recommendation="No action needed.",
    )
    rendered = format_review_summary(summary)

    assert "Overall: PASS" in rendered
    assert "No action needed." in rendered


def test_github_client_maps_auth_and_rate_limit_errors():
    client = GitHubClient(token="token")

    with pytest.raises(AuthenticationError):
        client._raise_for_status(401, "bad credentials")

    with pytest.raises(RateLimitError):
        client._raise_for_status(429, "rate limited")

    with pytest.raises(GitHubAPIError):
        client._raise_for_status(500, "failed")


def test_review_summary_formatting():
    summary = ReviewSummary(
        overall="NEEDS_CHANGES",
        total_findings=3,
        severity_counts={"CRITICAL": 1, "HIGH": 1, "MEDIUM": 1, "LOW": 0},
        category_counts={"SECURITY": 2, "QUALITY": 1},
        top_issues=["SQL injection risk", "Missing auth check"],
        recommendation="Fix before merge.",
    )

    rendered = format_review_summary(summary)

    assert "AI CODE REVIEW" in rendered
    assert "NEEDS_CHANGES" in rendered
    assert "CRITICAL: 1" in rendered
    assert "SQL injection risk" in rendered
