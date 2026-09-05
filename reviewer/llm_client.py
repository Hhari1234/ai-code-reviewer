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
    def __init__(self, api_key: str, model: str = "gemini-3.5-flash") -> None:
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

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise InvalidLLMResponseError("Gemini returned malformed JSON") from exc
