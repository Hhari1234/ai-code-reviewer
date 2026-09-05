from __future__ import annotations

import argparse

from .analyzer import ReviewEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Code Reviewer")
    parser.add_argument("--diff", type=str, default="", help="Unified diff content or path to a diff file")
    parser.add_argument("--file", type=str, default="", help="Optional file list input to review")
    args = parser.parse_args()

    diff_text = args.diff
    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            diff_text = handle.read()

    if not diff_text.strip():
        print("No diff content provided.")
        raise SystemExit(1)

    engine = ReviewEngine()
    result = engine.analyze_diff(diff_text)
    print(result.summary)
    for finding in result.findings:
        print(f"- {finding.severity}: {finding.title} ({finding.file}:{finding.line})")


if __name__ == "__main__":
    main()
