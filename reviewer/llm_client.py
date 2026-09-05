from __future__ import annotations

import json
import time
from typing import Any

import httpx

from .models import Finding


class InvalidLLMResponseError(ValueError):
    pass


class GeminiAPIError(ValueError):
    """Raised when Gemini API request fails after all retries."""

    def __init__(
        self,
        message: str,
        *,
        model: str,
        attempts: int,
        last_error: Exception | None = None,
    ) -> None:
        self.message = message
        self.model = model
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"GeminiAPIError(model={self.model}, attempts={self.attempts}): {self.message}"


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
    #: Maximum number of retry attempts for transient failures
    MAX_RETRIES = 3
    #: Initial backoff delay in seconds, will grow exponentially
    INITIAL_BACKOFF = 1.0
    #: Maximum backoff delay in seconds
    MAX_BACKOFF = 10.0

    def __init__(self, api_key: str, model: str = "gemini-3.8-flash") -> None:
        self.api_key = api_key.strip() if api_key else ""
        self.model = model

    def _do_generate(self, prompt: str) -> dict[str, Any]:
        """Single attempt to generate from Gemini without retry logic.

        Raises httpx.HTTPError for HTTP problems or InvalidLLMResponseError
        if the response cannot be parsed as valid JSON findings.
        """
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

    def generate(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        retryable_status_codes = {429, 500, 502, 503, 504}
        last_error: Exception | None = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return self._do_generate(prompt)
            except (httpx.HTTPError, InvalidLLMResponseError) as exc:
                last_error = exc

                # Check if this is a retryable HTTP status code
                http_exc = None
                if isinstance(exc, httpx.HTTPStatusError):
                    http_exc = exc
                    if http_exc.response.status_code not in retryable_status_codes:
                        # Permanent error - fail immediately
                        raise
                elif isinstance(exc, httpx.TimeoutException):
                    # Timeout is retryable
                    pass
                elif isinstance(exc, httpx.ConnectError):
                    # Connection error is retryable
                    pass

                # If this was the last attempt, raise the last error
                if attempt >= self.MAX_RETRIES:
                    break

                # Calculate backoff delay with exponential growth and jitter
                backoff = min(self.INITIAL_BACKOFF * (2 ** (attempt - 1)), self.MAX_BACKOFF)
                # Add small jitter to avoid thundering herd
                jitter = 0.1 * backoff * (0.5 + attempt * 0.1)
                delay = backoff + jitter

                # Check for Retry-After header
                if http_exc is not None and http_exc.response is not None:
                    retry_after = http_exc.response.headers.get("Retry-After")
                    if retry_after is not None:
                        try:
                            delay = float(retry_after)
                        except (ValueError, TypeError):
                            pass

                # Log retry information safely (no secrets)
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Gemini request attempt %d/%d failed: %s; retrying in %.1fs",
                    attempt,
                    self.MAX_RETRIES,
                    http_exc.response.status_code if http_exc else type(exc).__name__,
                    delay,
                )

                time.sleep(delay)

        # All retries exhausted - raise clear error
        raise GeminiAPIError(
            f"Gemini API request failed after {self.MAX_RETRIES} attempts",
            model=self.model,
            attempts=self.MAX_RETRIES,
            last_error=last_error,
        )

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
