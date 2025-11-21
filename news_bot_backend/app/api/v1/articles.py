from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.articles import Articles
from app.schemas.article import ArticleListResponse, ArticleRead, IngestRequest
from app.services.news_ingestion import ingest_sources

router = APIRouter(prefix="/articles", tags=["articles"])



@router.post("/ingest", response_model=ArticleListResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_articles(
    payload: IngestRequest,
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    articles = await ingest_sources(db, source_ids=payload.source_ids or None, limit=payload.limit)
    return ArticleListResponse(
        items=[ArticleRead.model_validate(article) for article in articles],
        total=len(articles),
    )

