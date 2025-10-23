import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status

from app.core.config import Settings, get_settings
from app.schemas import (
    FullAnalysisRequest,
    FullAnalysisResponse,
    NerRequest,
    NerResponse,
    SentimentRequest,
    SentimentResponse,
    SummarizationRequest,
    SummarizationResponse,
)
from app.services.pipeline import TextAnalyticsService


def create_app(settings: Settings) -> FastAPI:
    """Application factory for easier testing."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        logger = logging.getLogger(settings.LOGGER_NAME)
        logger.info("Starting ML microservice (version=%s)", settings.VERSION)
        try:
            yield
        finally:
            logger.info("Shutting down ML microservice")

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    service = TextAnalyticsService(settings)

    async def get_service() -> TextAnalyticsService:
        return service

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/summarize", response_model=SummarizationResponse, tags=["summarization"])
    async def summarize(
        payload: SummarizationRequest,
        svc: TextAnalyticsService = Depends(get_service),
    ) -> SummarizationResponse:
        try:
            summary = await svc.summarize(payload.text, min_tokens=payload.min_tokens, max_tokens=payload.max_tokens)
        except Exception as exc:  # pragma: no cover - defensive logging for unexpected errors
            logging.getLogger(settings.LOGGER_NAME).exception("Summarization failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Summarization failed: {exc}",
            ) from exc
        return SummarizationResponse(summary=summary)

    @app.post("/v1/sentiment", response_model=SentimentResponse, tags=["analysis"])
    async def sentiment(
        payload: SentimentRequest,
        svc: TextAnalyticsService = Depends(get_service),
    ) -> SentimentResponse:
        try:
            result = await svc.sentiment(payload.text)
        except Exception as exc:  # pragma: no cover
            logging.getLogger(settings.LOGGER_NAME).exception("Sentiment analysis failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Sentiment analysis failed: {exc}",
            ) from exc
        return SentimentResponse.from_dataclass(result)

    @app.post("/v1/ner", response_model=NerResponse, tags=["analysis"])
    async def ner(
        payload: NerRequest,
        svc: TextAnalyticsService = Depends(get_service),
    ) -> NerResponse:
        try:
            entities = await svc.ner(payload.text)
        except Exception as exc:  # pragma: no cover
            logging.getLogger(settings.LOGGER_NAME).exception("NER inference failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"NER inference failed: {exc}",
            ) from exc
        return NerResponse.from_dataclasses(entities)

    @app.post("/v1/analyze", response_model=FullAnalysisResponse, tags=["analysis"])
    async def analyze(
        payload: FullAnalysisRequest,
        svc: TextAnalyticsService = Depends(get_service),
    ) -> FullAnalysisResponse:
        try:
            results = await svc.full_analysis(
                payload.text,
                min_tokens=payload.min_tokens,
                max_tokens=payload.max_tokens,
            )
        except Exception as exc:  # pragma: no cover
            logging.getLogger(settings.LOGGER_NAME).exception("Full analysis failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Full analysis failed: {exc}",
            ) from exc
        ner_response = NerResponse.from_dataclasses(results["entities"])
        return FullAnalysisResponse(
            summary=results["summary"],
            sentiment=SentimentResponse.from_dataclass(results["sentiment"]),
            entities=ner_response.entities,
        )

    return app


settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
app = create_app(settings)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8100, reload=False)
