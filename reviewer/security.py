from __future__ import annotations

import re

from .models import Finding


class SecurityAnalyzer:
    def scan_text(self, text: str) -> list[Finding]:
        findings: list[Finding] = []
        lowered = text.lower()

        if re.search(r"(api[_-]?key|secret|token)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{8,}", text, re.IGNORECASE):
            findings.append(
                Finding(
                    file="",
                    line=1,
                    severity="HIGH",
                    category="SECURITY",
                    title="Hardcoded secret or API key",
                    description="A credential-like value appears to be embedded in source code.",
                    recommendation="Move secrets to environment variables or a secret manager.",
                    confidence=0.9,
                )
            )

        if "select * from" in lowered and "%s" in text.lower():
            findings.append(
                Finding(
                    file="",
                    line=1,
                    severity="HIGH",
                    category="SECURITY",
                    title="Potential SQL injection pattern",
                    description="Dynamic SQL construction is using string interpolation with user input.",
                    recommendation="Use parameterized queries or ORMs and validate untrusted input.",
                    confidence=0.82,
                )
            )

        if "subprocess.run" in lowered and "shell=true" in lowered:
            findings.append(
                Finding(
                    file="",
                    line=1,
                    severity="HIGH",
                    category="SECURITY",
                    title="Command injection risk",
                    description=(
                        "A subprocess call with shell execution can allow command "
                        "injection if arguments are influenced by users."
                    ),
                    recommendation="Avoid shell=True and validate or pass arguments as a list.",
                    confidence=0.88,
                )
            )

        if "password" in lowered and "hardcoded" in lowered:
            findings.append(
                Finding(
                    file="",
                    line=1,
                    severity="MEDIUM",
                    category="SECURITY",
                    title="Hardcoded password",
                    description="A password appears to be embedded directly in the codebase.",
                    recommendation="Use a secure secret store and inject via environment variables.",
                    confidence=0.8,
                )
            )

        return findings
