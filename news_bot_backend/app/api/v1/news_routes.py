from typing import Optional, Literal
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, contains_eager
from starlette import status

from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models import User, Articles, Source, UserSources, Topic
from app.services.dependencies import get_current_user
from app.schemas.article import ArticleRead, ArticleListResponse

router = APIRouter(prefix="/news", tags=["News"])

logger = get_logger(__name__)




@router.get("/get-news/", response_model=ArticleListResponse)
async def filter_articles(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        # Источники: all | subscriptions | single
        source_scope: Literal["all", "subscriptions", "single"] = Query(
            default="all",
        ),
        source_id: Optional[int] = Query(
            default=None,
        ),
        # Тема (по ID темы)
        topic_id: Optional[int] = Query(
            default=None,
        ),
        # Период: today | 3days | week
        period: Optional[Literal["today", "3days", "week"]] = Query(
            default=None,
        ),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
) -> ArticleListResponse:

    try:
        filters = []

        # Базовый запрос с загрузкой источника
        statement = (
            select(Articles)
            .join(Source, Articles.source_id == Source.id)
            .options(contains_eager(Articles.source))
        )

        # Фильтр по источникам
        if source_scope == "subscriptions":
            # Только источники, на которые подписан текущий пользователь
            statement = (
                statement
                .join(UserSources, UserSources.source_id == Source.id)
                .where(UserSources.user_id == current_user.id)
            )
        elif source_scope == "single":
            if source_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_id is required when source_scope='single'"
                )
            filters.append(Articles.source_id == source_id)

        # Фильтр по теме
        if topic_id is not None:
            filters.append(Articles.topic_id == topic_id)

        # Фильтр по периоду
        if period is not None:
            now = datetime.utcnow()
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
        count_stmt = (
            select(func.count())
            .select_from(Articles)
            .join(Source, Articles.source_id == Source.id)
        )

        if source_scope == "subscriptions":
            count_stmt = (
                count_stmt
                .join(UserSources, UserSources.source_id == Source.id)
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

@router.get("/search/", response_model=list[ArticleRead])
async def search_articles_by_title(
        title: str = Query(..., description="Title or part of title to search for"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        limit: Optional[int] = Query(default=100, ge=1, le=1000)
):

    logger.info(f"Searching all articles by title: '{title}'")

    try:
        # Create search pattern for partial matching
        search_pattern = f"%{title}%"

        # Search in ALL articles (no user subscription filter)
        # Use selectinload to eagerly load source relationship
        statement = (
            select(Articles)
            .options(selectinload(Articles.source))  # Eagerly load source relationship
            .where(Articles.title.ilike(search_pattern))  # Case-insensitive partial match
            .order_by(Articles.published_at.desc())
            .limit(limit)
        )

        result = await db.execute(statement)
        articles = result.scalars().all()

        logger.info(f"Found {len(articles)} articles matching '{title}'")
        return [ArticleRead.model_validate(article) for article in articles]

    except Exception as e:
        logger.error(f"Error during searching articles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during searching articles"
        )



