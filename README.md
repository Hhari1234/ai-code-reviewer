# AI Code Reviewer — GitHub-Native AI Code Review & Security Assistant

One-line description: A GitHub-native AI code review system that analyzes pull requests using Python, a review orchestration layer, Gemini-backed LLM reasoning, and structured classification for security, quality, and performance issues.

![CI](https://img.shields.io/badge/CI-configured-blue)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Demo

This repository combines the upstream PR-Agent review engine with an original engineering layer that normalizes GitHub diffs, filters noisy/generated files, classifies findings by severity, and emits structured review summaries back into GitHub workflows.

## Features

- GitHub PR metadata and diff retrieval
- Security-first static review heuristics
- Structured review findings with severity and category classification
- Duplicate-finding prevention and summary generation
- Gemini-based analysis abstraction
- GitHub Actions automation for PR review
- Dockerized local execution
- Automated unit test coverage for review core logic

## Architecture

The project retains the useful upstream PR-Agent functionality but adds a clear original review layer around it:

- GitHub client layer for repository metadata and review submission
- Diff parsing and file filtering
- Security and quality analyzers
- LLM abstraction for Gemini and future providers
- Structured review models and formatting
- CI and GitHub Action integration

## Tech stack

- Python 3.12
- PR-Agent foundation for PR review execution
- GitHub REST API
- Google Gemini via HTTPX
- FastAPI for lightweight API endpoints
- Pytest for automated validation
- Docker and GitHub Actions for automation

## How it works

1. A pull request is opened or updated.
2. The GitHub client fetches PR metadata and files.
3. The diff parser extracts changed hunks and filters irrelevant files.
4. Local security and quality heuristics inspect the patch.
5. An LLM layer can analyze the diff for nuanced findings.
6. Findings are deduplicated and classified by severity.
7. A summary is emitted to the GitHub review flow.

## Installation

```bash
git clone https://github.com/Hhari1234/ai-code-reviewer.git
cd ai-code-reviewer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Environment variables

Copy and populate the environment template:

```bash
cp .env.example .env
```

Supported configuration:

- `GITHUB_TOKEN`
- `GITHUB_API_URL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `MAX_DIFF_CHARS`
- `MAX_FILES`
- `LOG_LEVEL`

## Local usage

```bash
$env:PYTHONPATH='.'
python -m reviewer.cli --diff sample.patch
pytest tests/unit -q
```

## GitHub Actions setup

The repository includes a workflow in `.github/workflows/ai-review.yml` that triggers on pull request `opened`, `synchronize`, and `reopened` events. It installs dependencies, fetches the diff, analyzes it, and posts a review summary using GitHub and Gemini secrets.

## Example PR review

See [docs/example-review.md](docs/example-review.md).

## Example findings

- Hardcoded API key or secret detection
- Potential SQL injection pattern
- Command injection via `shell=True`
- Missing authorization or validation checks

## Supported review categories

- BUG
- SECURITY
- PERFORMANCE
- CODE_QUALITY
- MAINTAINABILITY
- TESTING
- ARCHITECTURE
- STYLE

## Testing

```bash
PYTHONPATH=. pytest tests/unit -q
```

## Docker

```bash
docker build -t ai-code-reviewer .
docker run -p 8000:8000 ai-code-reviewer
```

## Security

- Secrets are never committed to source control.
- GitHub tokens and API keys are expected from environment variables or GitHub Actions Secrets.
- Logging avoids printing credentials or tokens.
- Action permissions are intentionally narrow.

## Limitations

- The project uses heuristic checks for common patterns, so it is advisory rather than a static-analysis guarantee.
- Large diffs are deliberately truncated for cost control.
- Line-level GitHub comments require a deeper review integration than the scaffold implemented here.

## Future improvements

- Add richer PR comment mapping to exact file/line references
- Add provider abstraction beyond Gemini
- Expand static-analysis rule coverage
- Persist review state to suppress duplicate comments across update cycles

## Project structure

```text
ai-code-reviewer/
├── reviewer/
├── api/
├── docs/
├── tests/
├── .github/workflows/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── README.md
├── pyproject.toml
└── LICENSE
```

## License

MIT

> This repository retains the valuable upstream PR-Agent foundation for pull-request review execution, while the original engineering layer adds GitHub-native orchestration, structured findings, security-first logic, and production-oriented automation around that upstream base.
