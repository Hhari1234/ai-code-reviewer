-> AI Code Review Agent (PR-Agent)

A locally-hosted, AI-powered code review agent that automatically analyzes GitHub pull requests and posts structured feedback — summaries, review comments, and improvement suggestions — directly on the PR.

Built on top of the open-source [PR-Agent](https://github.com/The-PR-Agent/pr-agent) project, configured to run entirely on a local machine and integrated with the Google Gemini API for free, zero-cost inference.

->-> What it does

- **`review`** — Analyzes a pull request's diff and posts a structured code review (findings, security concerns, effort estimate) as a PR comment
- **`describe`** — Auto-generates a PR title and summary based on the actual code changes
- **`improve`** — Suggests specific, actionable code improvements as inline comments
- **`ask`** — Answers free-text questions about what a PR changes

-> Tech stack

- **Python 3.12** — core runtime
- **PR-Agent** — open-source PR review engine
- **LiteLLM** — unified interface for routing requests to different LLM providers
- **Google Gemini API** (`gemini-3.6-flash`) — free-tier LLM inference
- **GitHub REST API** — for fetching PR diffs and posting review comments
- **Rust + MSVC Build Tools** — required to compile native extensions used by LiteLLM on Windows

->-> Setup

->->-> Prerequisites
- Python 3.12+
- [Rust](https://rustup.rs/) (for compiling native dependencies)
- [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with "Desktop development with C++" workload (Windows only)
- A [GitHub personal access token](https://github.com/settings/tokens) with `repo` scope
- A free [Google Gemini API key](https://aistudio.google.com/apikey)

->->-> Installation

```bash
git clone https://github.com/Hhari1234/ai-code-reviewer.git
cd ai-code-reviewer
pip install -e .
```

->->-> Configuration

Credentials are kept out of version control via environment variables and a gitignored local settings file.

**Option A — Environment variables:**
```bash
setx GITHUB_TOKEN "your_github_token_here"
setx GEMINI_API_KEY "your_gemini_key_here"
```

**Option B — Local secrets file** (copy the template, fill in your own keys):
```bash
cp pr_agent/settings/.secrets_template.toml pr_agent/settings/.secrets.toml
-> then edit .secrets.toml with your own keys
```
> `.secrets.toml` is excluded via `.gitignore` and never committed.

->->-> Usage

```bash
pr-agent --pr_url <PR_URL> review --config.model="gemini/gemini-3.6-flash" --config.fallback_models=[]
```

Replace `<PR_URL>` with any real GitHub pull request URL, e.g.:
```bash
pr-agent --pr_url https://github.com/owner/repo/pull/123 review --config.model="gemini/gemini-3.6-flash" --config.fallback_models=[]
```

Swap `review` for `describe`, `improve`, or `ask "your question"` to run other tools.

->-> Notable setup challenges solved

- Diagnosed and resolved a native-extension build failure (`litellm` requires compiling Rust code via `maturin`/`pyo3`) by installing the Rust toolchain and MSVC Build Tools on Windows
- Migrated from OpenAI to Google Gemini as the inference provider to avoid billing dependency, using LiteLLM's model-routing layer
- Implemented secure credential handling to prevent API key leakage into version control

->-> License

This project builds on [PR-Agent](https://github.com/The-PR-Agent/pr-agent), licensed under MIT.
