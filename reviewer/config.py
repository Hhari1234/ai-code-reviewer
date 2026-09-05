from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class ReviewSettings:
    github_token: str = ""
    github_base_url: str = "https://api.github.com"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    max_diff_chars: int = 60000
    max_files: int = 30
    ignored_dirs: tuple[str, ...] = (
        ".git",
        "node_modules",
        "dist",
        "build",
        "coverage",
        ".venv",
        "venv",
        "__pycache__",
        "vendor",
        "target",
    )

    @classmethod
    def from_env(cls) -> "ReviewSettings":
        return cls(
            github_token=os.getenv("GITHUB_TOKEN", ""),
            github_base_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            max_diff_chars=int(os.getenv("MAX_DIFF_CHARS", "60000")),
            max_files=int(os.getenv("MAX_FILES", "30")),
        )


def get_settings() -> ReviewSettings:
    return ReviewSettings.from_env()
