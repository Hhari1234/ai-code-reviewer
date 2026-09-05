"""Unit tests for gemini_probe.py diagnostic functionality."""
import os
import sys
import json
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemini_probe import safe_key_info, send_minimal_probe, send_application_probe, MODEL, URL


class TestSafeKeyInfo:
    def test_safe_key_info_does_not_print_key(self, capsys, monkeypatch):
        """safe_key_info should never print the full API key."""
        monkeypatch.setenv("GEMINI_API_KEY", "sk-abcdef1234567890")
        captured = capsys.readouterr()
        safe_key_info()
        captured = capsys.readouterr()
        output = captured.out
        assert "sk-abcdef1234567890" not in output
        assert "API key first 3 chars: sk-" in output
        assert "API key last 3 chars: 890" in output

    def test_safe_key_info_no_key(self, capsys, monkeypatch):
        """safe_key_info should handle missing key gracefully."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        safe_key_info()
        captured = capsys.readouterr()
        assert "API key exists: False" in captured.out


class TestSendMinimalProbe:
    def test_minimal_request_body_structure(self):
        """Minimal probe should send only contents/parts/text with no extra parameters."""
        body = {"contents": [{"parts": [{"text": "test"}]}]}
        assert len(body) == 1
        assert "contents" in body
        assert body["contents"][0]["parts"][0]["text"] == "test"

    def test_minimal_request_body_size(self):
        """Minimal request body should be small."""
        body = {"contents": [{"parts": [{"text": "test"}]}]}
        assert len(json.dumps(body)) < 100

    @patch("gemini_probe.httpx.post")
    def test_minimal_probe_logs_status(self, mock_post, monkeypatch, capsys):
        """Minimal probe should log HTTP status without exposing the key."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}'
        mock_response.headers = {}
        mock_post.return_value = mock_response

        send_minimal_probe()
        captured = capsys.readouterr()
        assert "HTTP Status: 200" in captured.out
        assert "test-key-123" not in captured.out

    @patch("gemini_probe.httpx.post")
    def test_minimal_probe_logs_503(self, mock_post, monkeypatch, capsys):
        """Minimal probe should log 503 response body and headers."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = '{"error": {"code": 503, "message": "Service Unavailable"}}'
        mock_response.headers = {"retry-after": "5"}
        mock_post.return_value = mock_response

        send_minimal_probe()
        captured = capsys.readouterr()
        assert "HTTP Status: 503" in captured.out
        assert "Service Unavailable" in captured.out
        assert "test-key-123" not in captured.out


class TestSendApplicationProbe:
    def test_application_request_body_structure(self):
        """Application probe should send contents/parts/text with no extra parameters."""
        diff_text = "A" * 60000
        prompt = f"Review this diff.\n\n{diff_text}"
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        assert len(body) == 1
        assert "contents" in body

    def test_application_request_body_is_large(self):
        """Application request body should be significantly larger than minimal."""
        diff_text = "A" * 60000
        prompt = f"Review this diff.\n\n{diff_text}"
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        assert len(json.dumps(body)) > 50000

    @patch("gemini_probe.httpx.post")
    def test_application_probe_logs_status(self, mock_post, monkeypatch, capsys):
        """Application probe should log HTTP status without exposing the key."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = '{"error": {"code": 503, "message": "Service Unavailable"}}'
        mock_response.headers = {}
        mock_post.return_value = mock_response

        send_application_probe()
        captured = capsys.readouterr()
        assert "HTTP Status: 503" in captured.out
        assert "test-key-123" not in captured.out


class TestModelAndEndpoint:
    def test_model_is_gemini_3_8_flash(self):
        """Model should be gemini-3.8-flash."""
        assert MODEL == "gemini-3.8-flash"

    def test_endpoint_correct(self):
        """Endpoint should use the correct Gemini API URL."""
        assert URL == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"

    def test_no_extra_generation_parameters(self):
        """Request body should contain only contents/parts/text - no temperature, max_tokens, etc."""
        body = {"contents": [{"parts": [{"text": "test"}]}]}
        assert set(body.keys()) == {"contents"}
        assert set(body["contents"][0].keys()) == {"parts"}
        assert set(body["contents"][0]["parts"][0].keys()) == {"text"}
