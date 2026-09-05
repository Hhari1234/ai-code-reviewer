# Example Review

This document is a fictional example illustrating how the tooling formats a GitHub review.

## Pull request

A backend endpoint accepts an `order_id` from the request and builds an inline SQL statement without parameterization.

## Detection

The diff parser identifies the changed file and the security analyzer flags the dynamic SQL pattern.

## Structured finding

```json
{
  "file": "src/orders.py",
  "line": 42,
  "severity": "HIGH",
  "category": "SECURITY",
  "title": "Potential SQL injection pattern",
  "description": "Dynamic SQL construction uses untrusted input directly in the query string.",
  "recommendation": "Use parameterized queries and validate request input.",
  "confidence": 0.88
}
```

## Summary output

```text
AI CODE REVIEW

Overall: NEEDS_CHANGES

Findings:
- CRITICAL: 0
- HIGH: 1
- MEDIUM: 0
- LOW: 0
- INFO: 0

Recommendation:
Address HIGH and CRITICAL findings before merging.
```
