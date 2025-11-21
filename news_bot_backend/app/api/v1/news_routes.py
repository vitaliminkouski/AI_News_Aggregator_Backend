from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models import User, Articles, Source, UserSources
from app.services.dependencies import get_current_user

router = APIRouter()

logger = get_logger(__name__)


@router.get("/news/")
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
