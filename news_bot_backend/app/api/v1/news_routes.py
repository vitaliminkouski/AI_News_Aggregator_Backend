from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models import User, Articles, Source, UserSources, Topic
from app.services.dependencies import get_current_user
from app.schemas.article import ArticleRead, ArticleListResponse

router = APIRouter(prefix="/news", tags=["News"])

logger = get_logger(__name__)


@router.get("/user-news/")
async def get_articles(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        limit: Optional[int] = Query(default=100, ge=1, le=1000)
):
    logger.info("Attempt to retrieve articles from database")
    statement = (
        select(Articles)
        .join(Source, Articles.source_id == Source.id)
        .join(UserSources, UserSources.source_id == Source.id)
        .where(UserSources.user_id == current_user.id)
        .order_by(Articles.published_at.desc())
        .limit(limit)
    )
    try:
        result = await db.execute(statement)
        return result.scalars().all()
    except:
        logger.error("Error during retrieving articles from database")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during retrieving articles from database"
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


@router.get("/", response_model=ArticleListResponse)
async def get_all_articles(
        db: AsyncSession = Depends(get_db),
        limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of results"),
        offset: int = Query(default=0, ge=0, description="Pagination offset")
) -> ArticleListResponse:
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


@router.get("/topic/{topic_id}/", response_model=ArticleListResponse)
async def get_articles_by_topic(
        topic_id: int,
        db: AsyncSession = Depends(get_db),
        limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of results"),
        offset: int = Query(default=0, ge=0, description="Pagination offset")
) -> ArticleListResponse:
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
