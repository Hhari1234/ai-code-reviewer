from __future__ import annotations

import re
from typing import Iterable

from .models import DiffEntry, DiffHunk


class DiffParser:
    _file_re = re.compile(r"^diff --git a/(.+?) b/(.+)$")

    @staticmethod
    def parse(diff_text: str) -> list[DiffEntry]:
        if not diff_text or not diff_text.strip():
            return []

        entries: list[DiffEntry] = []
        current_entry: DiffEntry | None = None
        current_hunk: DiffHunk | None = None

        for line in diff_text.splitlines():
            if line.startswith("diff --git "):
                if current_entry is not None:
                    entries.append(current_entry)
                match = DiffParser._file_re.match(line)
                if match:
                    file_path = match.group(2).strip()
                    current_entry = DiffEntry(file_path=file_path, status="modified")
                    current_hunk = None
                else:
                    current_entry = DiffEntry(file_path="", status="modified")
                    current_hunk = None
                continue

            if current_entry is None:
                continue

            if line.startswith("@@ "):
                current_hunk = DiffHunk(header=line)
                current_entry.hunks.append(current_hunk)
                continue

            if current_hunk is not None:
                current_hunk.content += f"{line}\n"

        if current_entry is not None:
            entries.append(current_entry)

        return entries

    @staticmethod
    def filter_irrelevant_files(paths: Iterable[str]) -> list[str]:
        ignored_dirs = {
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
        }
        ignored_suffixes = (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".lock",
            ".pyc",
            ".min.js",
            ".bundle.js",
            ".map",
            ".sqlite",
            ".db",
            ".log",
            ".pdf",
            ".zip",
            ".tar",
            ".gz",
        )
        ignored_names = {
            "package-lock.json",
            "yarn.lock",
            "poetry.lock",
            "pnpm-lock.yaml",
            "coverage.xml",
            "coverage.json",
            "gemfile.lock",
        }

        filtered: list[str] = []
        for raw in paths:
            path = str(raw).strip()
            if not path:
                continue
            lower = path.lower()
            if any(part in ignored_dirs for part in lower.split("/")):
                continue
            if lower.endswith(ignored_suffixes):
                continue
            if lower.rsplit("/", 1)[-1] in ignored_names:
                continue
            if lower.startswith("dist/") or lower.startswith("build/"):
                continue
            filtered.append(path)
        return filtered
