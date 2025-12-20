from __future__ import annotations

from typing import Optional, Sequence, Literal
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.articles import Articles
from app.models.source import Source
from app.models.topic import Topic
from app.schemas.article import ArticleListResponse, ArticleRead, IngestRequest
from app.services.news_ingestion import ingest_sources
from app.models.user_sources import UserSources
from app.core.config import settings
from app.core.logging_config import get_logger

from app.services.dependencies import get_current_user

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


@router.get("/filter/", response_model=ArticleListResponse)
async def filter_articles(
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        source_scope: Literal["all", "subscriptions", "single"] = Query(
            default="all",
            description="Источник новостей: all — все, subscriptions — только подписки пользователя, single — конкретный источник"
        ),
        source_id: Optional[int] = Query(
            default=None,
            description="ID конкретного источника (обязателен, если source_scope=single)"
        ),
        topic_id: Optional[int] = Query(
            default=None,
            description="ID темы (например, Спорт, Культура и т.д.)"
        ),
        period: Optional[Literal["today", "3days", "week"]] = Query(
            default=None,
            description="Период: today — за сегодня, 3days — за 3 дня, week — за неделю"
        ),
        limit: int = Query(default=100, ge=1, le=1000, description="Максимальное количество результатов"),
        offset: int = Query(default=0, ge=0, description="Смещение для пагинации"),
) -> ArticleListResponse:
    try:
        filters = []

        # Базовый запрос с загрузкой источника
        statement = (
            select(Articles)
            .options(selectinload(Articles.source))
        )

        # 1. Фильтр по источникам
        if source_scope == "subscriptions":
            statement = (
                statement
                .join(UserSources, UserSources.source_id == Articles.source_id)
                .where(UserSources.user_id == current_user.id)
            )
        elif source_scope == "single":
            if source_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_id is required when source_scope='single'"
                )
            filters.append(Articles.source_id == source_id)

        # 2. Фильтр по теме - теперь используем Articles.topic_id напрямую
        if topic_id is not None:
            filters.append(Articles.topic_id == topic_id)

        # 3. Фильтр по периоду
        if period is not None:
            now = datetime.now(timezone.utc)
            if period == "today":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "3days":
                start = now - timedelta(days=3)
            elif period == "week":
                start = now - timedelta(days=7)
            else:
                start = None

            if start is not None:
                filters.append(Articles.published_at >= start)

        # Применяем все накопленные фильтры
        if filters:
            statement = statement.where(*filters)

        # Считаем total до пагинации
        count_stmt = select(func.count()).select_from(Articles)

        if source_scope == "subscriptions":
            count_stmt = (
                count_stmt
                .join(UserSources, UserSources.source_id == Articles.source_id)
                .where(UserSources.user_id == current_user.id)
            )
        if filters:
            count_stmt = count_stmt.where(*filters)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Пагинация
        statement = statement.order_by(Articles.published_at.desc()).offset(offset).limit(limit)

        result = await db.execute(statement)
        articles = result.scalars().all()

        return ArticleListResponse(
            items=[ArticleRead.model_validate(a) for a in articles],
            total=total,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error filtering articles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during filtering articles"
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
    Returns articles that belong to the specified topic (using Articles.topic_id).
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
        
        # Теперь используем Articles.topic_id напрямую
        statement = (
            select(Articles)
            .where(Articles.topic_id == topic_id)
            .options(selectinload(Articles.source))
            .order_by(Articles.published_at.desc())
        )
        
        # Get total count before pagination
        count_statement = (
            select(func.count())
            .select_from(Articles)
            .where(Articles.topic_id == topic_id)
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

