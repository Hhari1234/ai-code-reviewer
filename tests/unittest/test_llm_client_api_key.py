import pytest

from reviewer.llm_client import GeminiClient


class TestGeminiClientAPIKey:
    def test_api_key_strips_trailing_newline(self):
        """API key with trailing newline should be stripped to prevent LocalProtocolError."""
        client = GeminiClient(api_key="abc123\n", model="gemini-3.8-flash")
        assert client.api_key == "abc123"
        assert "\n" not in client.api_key

    def test_api_key_strips_leading_whitespace(self):
        """API key with leading whitespace should be stripped."""
        client = GeminiClient(api_key="  abc123", model="gemini-3.8-flash")
        assert client.api_key == "abc123"

    def test_api_key_strips_both_sides(self):
        """API key with whitespace on both sides should be stripped."""
        client = GeminiClient(api_key="  abc123  ", model="gemini-3.8-flash")
        assert client.api_key == "abc123"

    def test_api_key_no_whitespace_unchanged(self):
        """API key without whitespace should remain unchanged."""
        client = GeminiClient(api_key="abc123", model="gemini-3.8-flash")
        assert client.api_key == "abc123"

    def test_api_key_empty_string(self):
        """Empty string should result in empty api_key."""
        client = GeminiClient(api_key="", model="gemini-3.8-flash")
        assert client.api_key == ""

    def test_api_key_none_handled(self):
        """None should result in empty api_key (falsy path)."""
        client = GeminiClient(api_key=None, model="gemini-3.8-flash")
        assert client.api_key == ""

    def test_api_key_cr_lf_removed(self):
        """Windows-style CRLF should be removed."""
        client = GeminiClient(api_key="abc123\r\n", model="gemini-3.8-flash")
        assert client.api_key == "abc123"
        assert "\r" not in client.api_key

    def test_api_key_carriage_return_removed(self):
        """Carriage return should be removed."""
        client = GeminiClient(api_key="abc123\r", model="gemini-3.8-flash")
        assert client.api_key == "abc123"
        assert "\r" not in client.api_key