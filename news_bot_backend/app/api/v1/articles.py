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


@router.get("/", response_model=ArticleListResponse)
async def list_articles(
    *,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    source_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
) -> ArticleListResponse:
    query = (
        select(Articles)
        .options(selectinload(Articles.source))
        .order_by(Articles.published_at.desc().nulls_last(), Articles.id.desc())
        .limit(limit)
        .offset(offset)
    )
    count_query = select(func.count(Articles.id))

    if source_id:
        query = query.where(Articles.source_id == source_id)
        count_query = count_query.where(Articles.source_id == source_id)
    if search:
        query = query.where(Articles.title.ilike(f"%{search}%"))
        count_query = count_query.where(Articles.title.ilike(f"%{search}%"))

    result = await db.execute(query)
    articles = result.scalars().all()
    total = await db.scalar(count_query) or 0

    return ArticleListResponse(
        items=[ArticleRead.model_validate(article) for article in articles],
        total=total,
    )


@router.get("/{article_id}", response_model=ArticleRead)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)) -> ArticleRead:
    result = await db.execute(
        select(Articles)
            .options(selectinload(Articles.source))
            .where(Articles.id == article_id)
    )
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return ArticleRead.model_validate(article)


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

