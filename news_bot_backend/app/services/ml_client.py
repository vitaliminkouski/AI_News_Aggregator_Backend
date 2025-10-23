from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel

from app.core.config import settings


class MLServiceError(Exception):
    """Raised when the ML microservice returns an error or is unreachable."""


class SentimentResult(BaseModel):
    label: str
    score: float


class EntityResult(BaseModel):
    text: str
    type: str
    score: float


class SummaryResult(BaseModel):
    summary: str


class AnalysisResult(BaseModel):
    summary: str
    sentiment: SentimentResult
    entities: list[EntityResult]


class MLClient:
    """Thin HTTPX wrapper around the ML microservice endpoints."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: Optional[httpx.Timeout] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout or httpx.Timeout(30.0, connect=5.0)

    async def summarize(
        self,
        text: str,
        *,
        min_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> SummaryResult:
        payload: Dict[str, Any] = {"text": text}
        if min_tokens is not None:
            payload["min_tokens"] = min_tokens
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        data = await self._post("/v1/summarize", payload)
        return SummaryResult.model_validate(data)

    async def analyze(
        self,
        text: str,
        *,
        min_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> AnalysisResult:
        payload: Dict[str, Any] = {"text": text}
        if min_tokens is not None:
            payload["min_tokens"] = min_tokens
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        data = await self._post("/v1/analyze", payload)
        return AnalysisResult.model_validate(data)

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
        except httpx.HTTPError as exc:  # pragma: no cover - network failure guard
            raise MLServiceError(f"Failed to reach ML service at {url}") from exc

        if response.status_code >= 400:
            raise MLServiceError(f"ML service returned {response.status_code}: {response.text}")
        return response.json()


ml_client = MLClient(settings.ML_SERVICE_URL)
