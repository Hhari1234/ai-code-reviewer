from __future__ import annotations

import os
from typing import Any

import requests


class GitHubAPIError(RuntimeError):
    pass


class AuthenticationError(GitHubAPIError):
    pass


class RateLimitError(GitHubAPIError):
    pass


class GitHubClient:
    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.base_url = (base_url or os.getenv("GITHUB_API_URL", "https://api.github.com")).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _raise_for_status(self, status_code: int, message: str) -> None:
        if status_code == 401:
            raise AuthenticationError(f"GitHub authentication failed: {message}")
        if status_code == 403:
            raise RateLimitError(f"GitHub rate limit or forbidden: {message}")
        if status_code == 429:
            raise RateLimitError(f"GitHub rate limit reached: {message}")
        if status_code >= 400:
            raise GitHubAPIError(f"GitHub API error {status_code}: {message}")

    def get_pr(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        response = self.session.get(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}")
        self._raise_for_status(response.status_code, response.text)
        return response.json()

    def get_changed_files(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files")
        self._raise_for_status(response.status_code, response.text)
        return response.json()

    def get_diff(self, owner: str, repo: str, pr_number: int) -> str:
        response = self.session.get(
            f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
            params={"accept": "application/vnd.github.v3.diff"},
        )
        self._raise_for_status(response.status_code, response.text)
        return response.text

    def create_review(self, owner: str, repo: str, pr_number: int, body: str, event: str = "COMMENT") -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            json={"body": body, "event": event},
        )
        self._raise_for_status(response.status_code, response.text)
        return response.json()

    def list_reviews(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews")
        self._raise_for_status(response.status_code, response.text)
        return response.json()
