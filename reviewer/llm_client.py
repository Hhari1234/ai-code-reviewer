from __future__ import annotations

import json
from typing import Any

import httpx

from .models import Finding


class InvalidLLMResponseError(ValueError):
    pass


class LLMResponseParser:
    @staticmethod
    def parse(payload: dict[str, Any]) -> "LLMReviewResult":
        if not isinstance(payload, dict):
            raise InvalidLLMResponseError("LLM payload must be a JSON object")

        findings = payload.get("findings")
        if findings is None:
            raise InvalidLLMResponseError("LLM response missing 'findings' field")

        parsed_findings = [
            Finding.from_dict(item)
            for item in findings
            if isinstance(item, dict)
        ]
        if not isinstance(findings, list):
            raise InvalidLLMResponseError("LLM findings must be a list")

        summary = payload.get("summary", "")
        return LLMReviewResult(findings=parsed_findings, summary=str(summary))


class LLMReviewResult:
    def __init__(self, findings: list, summary: str = "") -> None:
        self.findings = findings
        self.summary = summary


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-3.8-flash") -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        url = "https://generativelanguage.googleapis.com/v1beta/models/" + self.model + ":generateContent"
        response = httpx.post(
            url,
            headers={"x-goog-api-key": self.api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not text:
            raise InvalidLLMResponseError("Empty response from Gemini")

        # Try to extract JSON from the response, handling potential markdown code blocks
        parsed = self._extract_json_from_text(text)
        if parsed is None:
            raise InvalidLLMResponseError("Gemini returned unparseable response")

        return parsed

    @staticmethod
    def _extract_json_from_text(text: str) -> dict[str, Any] | None:
        """Extract a JSON object from Gemini's response text.

        Gemini may return text with markdown fences (```json ... ```) or surrounding
        prose. This method safely extracts the JSON object regardless.
        """
        s = text.strip()

        # Remove ```json ... ``` or ``` ... ``` code fences if present
        if s.startswith("```"):
            # Find the end fence
            lines = s.splitlines()
            # Remove leading fence
            if len(lines) > 1 and lines[1].strip().startswith("json"):
                # Has ```json ``` fence - extract content between fences
                # Find the closing fence
                in_fence = True
                result_lines = []
                for line in lines[2:]:
                    if line.strip() == "```":
                        in_fence = False
                        break
                    result_lines.append(line)
                if not in_fence:
                    s = "\n".join(result_lines).strip()

        # Try to find the innermost JSON object
        # Strategy: try direct parse first, then search for JSON object
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass

        # If direct parse failed, search for a JSON object within the text
        # Try progressively smaller substrings from the center outward
        for start in range(len(s)):
            for end in range(len(s), start, -1):
                candidate = s[start:end]
                # Quick check: must start with { and end with }
                if not candidate.startswith("{"):
                    continue
                if not candidate.endswith("}"):
                    continue
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue

        return None
