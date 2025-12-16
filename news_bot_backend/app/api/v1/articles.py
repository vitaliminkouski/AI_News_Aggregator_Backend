from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.articles import Articles
from app.models.source import Source
from app.models.topic import Topic
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


@router.get("/", response_model=ArticleListResponse)
async def get_all_articles(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset")
) -> ArticleListResponse:
    """
    Get all articles with pagination.
    Returns all articles ordered by published date (newest first).
    """
    try:
        # Base query with source relationship loaded
        statement = (
            select(Articles)
            .options(selectinload(Articles.source))
            .order_by(Articles.published_at.desc())
        )
        
        # Get total count before pagination
        count_statement = select(func.count()).select_from(Articles)
        total_result = await db.execute(count_statement)
        total = total_result.scalar() or 0
        
        # Apply pagination
        statement = statement.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(statement)
        articles = result.scalars().all()
        
        return ArticleListResponse(
            items=[ArticleRead.model_validate(article) for article in articles],
            total=total
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving articles: {str(e)}"
        )


@router.get("/topic/{topic_id}", response_model=ArticleListResponse)
async def get_articles_by_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset")
) -> ArticleListResponse:
    """
    Get articles by topic ID.
    Returns articles from sources that belong to the specified topic.
    """
    try:
        # Verify topic exists
        topic_result = await db.execute(select(Topic).where(Topic.id == topic_id))
        topic = topic_result.scalar_one_or_none()
        
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic with id {topic_id} not found"
            )
        
        # Query: Articles -> Source -> Topic
        # Get articles from sources that belong to this topic
        statement = (
            select(Articles)
            .join(Source, Articles.source_id == Source.id)
            .where(Source.topic_id == topic_id)
            .options(selectinload(Articles.source))
            .order_by(Articles.published_at.desc())
        )
        
        # Get total count before pagination
        count_statement = (
            select(func.count())
            .select_from(Articles)
            .join(Source, Articles.source_id == Source.id)
            .where(Source.topic_id == topic_id)
        )
        total_result = await db.execute(count_statement)
        total = total_result.scalar() or 0
        
        # Apply pagination
        statement = statement.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(statement)
        articles = result.scalars().all()
        
        return ArticleListResponse(
            items=[ArticleRead.model_validate(article) for article in articles],
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving articles by topic: {str(e)}"
        )

