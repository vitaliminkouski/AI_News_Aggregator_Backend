
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models import User, Topic
from app.schemas.topic import TopicReturn, TopicCreate
from app.services.dependencies import get_current_user, get_superuser

router=APIRouter(prefix="/topic", tags=["topic"])

logger=get_logger(__name__)

@router.get("/", response_model=list[TopicReturn])
async def get_all_topics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[TopicReturn]:
    res = await db.execute(select(Topic))
    topics = res.scalars().all()
    return [TopicReturn.model_validate(topic) for topic in topics]

@router.post("/")
async def create_topic(
        data: TopicCreate,
        db: AsyncSession=Depends(get_db),
        user: User=Depends(get_superuser)
):
    res = await db.execute(select(Topic).where(Topic.name == data.name))
    existing = res.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Topic {data.name} already exists"
        )
    try:



        topic=Topic(name=data.name)
        db.add(topic)
        await db.commit()
        await db.refresh(topic)
        logger.info(f"Topic {topic.name} has been created")
        return {
            "status_code": 201,
            "detail": f"Topic {topic.name} has been created"
        }
    except:
        logger.error(f"Error during creating topic {data.name}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during creating topic in database"
        )

@router.delete("/")
async def delete_topic(
        topic_id: int,
        superuser: User=Depends(get_superuser),
        db: AsyncSession=Depends(get_db)
):
    topic=await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(
            status_code=404,
            detail=f"Topic with id {topic_id} not found"
        )
    try:
        await db.delete(topic)
        await db.commit()
        return {"message": f"Topic with id {topic_id} has been deleted successfully"}
    except:
        raise HTTPException(
            status_code=500,
            detail="Error during deleting topic"
        )