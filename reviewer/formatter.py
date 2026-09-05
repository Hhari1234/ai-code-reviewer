from __future__ import annotations

from .models import ReviewSummary


def format_review_summary(summary: ReviewSummary) -> str:
    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    if summary.total_findings == 0:
        return (
            "AI CODE REVIEW\n\n"
            "Overall: PASS\n\n"
            f"Findings:\n- CRITICAL: 0\n- HIGH: 0\n- MEDIUM: 0\n- LOW: 0\n- INFO: 0\n\n"
            f"Recommendation:\n{summary.recommendation}\n"
        )

    lines = [
        "AI CODE REVIEW",
        "",
        f"Overall: {summary.overall}",
        "",
        "Findings:",
    ]

    for level in severity_order:
        lines.append(f"- {level}: {summary.severity_counts.get(level, 0)}")

    if summary.category_counts:
        lines.extend(["", "Categories:"])
        for category, count in summary.category_counts.items():
            lines.append(f"- {category}: {count}")

    if summary.top_issues:
        lines.extend(["", "Top issues:"])
        for index, issue in enumerate(summary.top_issues[:5], start=1):
            lines.append(f"{index}. {issue}")

    lines.extend(["", "Recommendation:"])
    lines.append(summary.recommendation)
    return "\n".join(lines) + "\n"
