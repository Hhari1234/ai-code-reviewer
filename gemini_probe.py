"""Minimal Gemini probe to diagnose 503 errors from GitHub Actions.

Sends ONLY the minimal request (contents/parts/text) with no extra
generation parameters. Compares with the application's full prompt request.
Never prints the API key.
"""
import os
import sys
import json
import httpx

MODEL = "gemini-3.8-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

def safe_key_info():
    """Log safe API key diagnostics without exposing the key."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    print(f"API key exists: {bool(api_key)}")
    print(f"API key length: {len(api_key)}")
    if api_key:
        print(f"API key first 3 chars: {api_key[:3]}")
        print(f"API key last 3 chars: {api_key[-3:]}")
        print(f"API key stripped length: {len(api_key.strip())}")
        print(f"strip() changes length: {len(api_key) != len(api_key.strip())}")

def send_minimal_probe():
    """Send the minimal request matching the known-working PowerShell test."""
    body = {"contents": [{"parts": [{"text": "test"}]}]}
    body_size = len(json.dumps(body))
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    print(f"\n--- Minimal Gemini Probe ---")
    print(f"Model: {MODEL}")
    print(f"Endpoint: {URL}")
    print(f"HTTP Method: POST")
    print(f"Request body size: {body_size} bytes")
    safe_key_info()

    try:
        response = httpx.post(
            URL,
            headers={"x-goog-api-key": api_key},
            json=body,
            timeout=30,
        )
        print(f"HTTP Status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        if response.status_code != 200:
            try:
                print(f"Response body: {response.text[:500]}")
            except Exception:
                print(f"Response body: (unable to read)")
        return response
    except httpx.LocalProtocolError as e:
        print(f"LocalProtocolError: {e}")
        return None
    except httpx.HTTPStatusError as e:
        print(f"HTTPStatusError: {e.response.status_code}")
        print(f"Response body: {e.response.text[:500] if e.response.text else '(empty)'}")
        return e.response
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return None

def send_application_probe():
    """Send the application's full prompt request to test body size impact."""
    diff_text = "A" * 60000
    trimmed = diff_text[:60000]
    prompt = (
        "You are an expert code reviewer. Return STRICT JSON ONLY with two keys: "
        "'findings' (array of objects) and 'summary' (string). "
        "Do NOT include any markdown code fences, explanations, or prose outside the JSON. "
        "Do NOT return any text before or after the JSON object. "
        "The JSON must be valid and parseable by json.loads() directly.\n\n"
        "Each finding object must have these exact keys: file, line, severity, category, title, description, recommendation.\n\n"
        'Return JSON in this exact format (NO markdown, NO fences, just the JSON object):\n'
        '{"findings": [{"file": "path/to/file.py", "line": 42, "severity": "high", "category": "security", "title": "XSS vulnerability", "description": "User input not sanitized", "recommendation": "Sanitize user input before rendering"}], '
        '"summary": "Found 1 security issue"}\n\n'
        f"Review this pull request diff and return the JSON strictly as specified above.\n\n"
        f"Files considered: ['file.py'].\n\n{trimmed}"
    )
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    body_size = len(json.dumps(body))
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    print(f"\n--- Application Probe ---")
    print(f"Model: {MODEL}")
    print(f"Endpoint: {URL}")
    print(f"HTTP Method: POST")
    print(f"Request body size: {body_size} bytes")
    safe_key_info()

    try:
        response = httpx.post(
            URL,
            headers={"x-goog-api-key": api_key},
            json=body,
            timeout=30,
        )
        print(f"HTTP Status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        if response.status_code != 200:
            try:
                print(f"Response body: {response.text[:500]}")
            except Exception:
                print(f"Response body: (unable to read)")
        return response
    except httpx.LocalProtocolError as e:
        print(f"LocalProtocolError: {e}")
        return None
    except httpx.HTTPStatusError as e:
        print(f"HTTPStatusError: {e.response.status_code}")
        print(f"Response body: {e.response.text[:500] if e.response.text else '(empty)'}")
        return e.response
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("Gemini 503 Diagnostic Probe")
    print("=" * 60)

    minimal_resp = send_minimal_probe()
    app_resp = send_application_probe()

    print(f"\n--- Summary ---")
    if minimal_resp and minimal_resp.status_code == 200:
        print("Minimal request: SUCCESS (200)")
    elif minimal_resp:
        print(f"Minimal request: FAILED ({minimal_resp.status_code})")
    else:
        print("Minimal request: ERROR")

    if app_resp and app_resp.status_code == 200:
        print("Application request: SUCCESS (200)")
    elif app_resp:
        print(f"Application request: FAILED ({app_resp.status_code})")
    else:
        print("Application request: ERROR")

    if minimal_resp and app_resp:
        if minimal_resp.status_code == 200 and app_resp.status_code != 200:
            print("\nROOT CAUSE: Request body size likely causes 503")
            print("Minimal request works but application's large prompt fails")
        elif minimal_resp.status_code != 200:
            print("\nROOT CAUSE: Gemini API unavailable from GitHub Actions")
            print("Both minimal and application requests fail - likely network/service issue")
        else:
            print("\nBoth requests succeeded - 503 may be intermittent or caused by other factors")
