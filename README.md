# AI Code Reviewer

An automated AI-powered GitHub pull-request code review system that analyzes PR diffs using **Gemini 3.8 Flash** and posts structured review findings directly to GitHub.

## Demo

See the verified E2E demo in [PR #5](https://github.com/Hhari1234/ai-code-reviewer/pull/5).

## Architecture

```
Developer opens PR
       ↓
GitHub Actions
       ↓
Diff extraction
       ↓
Static/security analysis
       ↓
Gemini 3.8 Flash
       ↓
Structured JSON response
       ↓
Finding validation/parsing
       ↓
GitHub PR review
```

## Features

- Gemini-powered code review using Gemini 3.8 Flash
- GitHub Actions integration for automated PR review
- GitHub REST API integration for diff fetching and review posting
- Structured findings with severity classification (CRITICAL, HIGH, MEDIUM, LOW, INFO)
- Security analysis for common vulnerabilities (hardcoded secrets, SQL injection, command injection)
- Diff parsing with irrelevant file filtering
- LLM response validation and parsing
- Retry and backoff handling for transient API failures
- Graceful error handling
- CLI support for local execution

## Technology Stack

- Python 3.12
- Gemini 3.8 Flash (Google AI)
- GitHub Actions
- GitHub REST API
- HTTPX for API calls
- Pytest for testing
- Ruff for linting

## Setup

### Prerequisites

- Python 3.12+
- A Google Gemini API key

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional - defaults to gemini-3.8-flash
GEMINI_MODEL=gemini-3.8-flash

# Optional
GITHUB_TOKEN=your_github_token_here
LOG_LEVEL=INFO
MAX_DIFF_CHARS=60000
MAX_FILES=100
```

### Installation

```bash
git clone https://github.com/Hhari1234/ai-code-reviewer.git
cd ai-code-reviewer
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Local Usage

```bash
# Set PYTHONPATH
export PYTHONPATH=.  # On Windows: $env:PYTHONPATH="."

# Run the reviewer
python .github/workflows/review_script.py
```

### GitHub Actions

The project includes a workflow in `.github/workflows/ai-review.yml` that:

1. Triggers on PR `opened`, `synchronize`, and `reopened` events
2. Fetches PR diff and metadata
3. Runs static/security analysis
4. Invokes Gemini 3.8 Flash for AI analysis
5. Posts structured review findings to the PR

Configure `GEMINI_API_KEY` and `GITHUB_TOKEN` as GitHub Actions secrets.

## End-to-End Verification

The system was verified against a real GitHub pull request ([PR #5](https://github.com/Hhari1234/ai-code-reviewer/pull/5)).

### Verified Flow

```
GitHub PR → GitHub Actions → Gemini 3.8 Flash → parsed finding → GitHub PR review
```

### Confirmed Results

| Metric | Status |
|--------|--------|
| Gemini Invoked | YES |
| Gemini HTTP Status | 200 |
| Response Parsed | YES |
| Findings Generated | YES |
| Review Posted to PR | YES |
| Review Contains Gemini Findings | YES |

The E2E test confirmed that:
- Gemini 3.8 Flash was actually invoked
- Gemini returned HTTP 200 with a valid response
- The response was successfully parsed into structured findings
- At least one Gemini-generated finding was produced
- The finding was posted to the pull request
- The posted review contained the Gemini-generated finding, not only static-analysis results

## Testing

```bash
# Run unit tests
PYTHONPATH=. pytest tests/unittest -v

# Run specific test files
PYTHONPATH=. pytest tests/unittest/test_llm_client_api_key.py -v
PYTHONPATH=. pytest tests/unittest/test_gemini_probe.py -v
```

## Security

- Secrets are never committed to source control
- API keys are read from environment variables
- GitHub tokens are expected from GitHub Actions secrets
- Credentials are stripped and sanitized before logging
- Action permissions are intentionally narrow (read contents, write pull-requests)

## Limitations

- Advisory rather than a static-analysis guarantee
- Large diffs are truncated for cost control
- Line-level GitHub comments require deeper integration

## Project Links

- **Source Code**: https://github.com/Hhari1234/ai-code-reviewer
- **E2E Demo**: https://github.com/Hhari1234/ai-code-reviewer/pull/5

## License

MIT
