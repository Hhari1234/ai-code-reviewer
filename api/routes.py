from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="AI Code Reviewer API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/review")
def review() -> dict[str, str]:
    return {"status": "accepted", "message": "Review queued"}


@app.get("/reviews/{review_id}")
def get_review(review_id: str) -> dict[str, str]:
    return {"review_id": review_id, "status": "not_implemented"}
