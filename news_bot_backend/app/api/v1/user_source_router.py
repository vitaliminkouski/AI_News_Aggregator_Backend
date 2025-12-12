from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models import User, Source, UserSources
from app.schemas.user_sources import UserSourceCreate, UserSourceRead
from app.services.dependencies import get_current_user

router = APIRouter(prefix="/user-sources", tags=["user-sources"])

@router.post("/", response_model=UserSourceRead, status_code=status.HTTP_201_CREATED)
async def add_user_source(
    payload: UserSourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSourceRead:
    # Validate source exists
    res = await db.execute(select(Source).where(Source.id == payload.source_id))
    source = res.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Check duplicate subscription
    exists = await db.execute(
        select(UserSources).where(
            UserSources.user_id == current_user.id,
            UserSources.source_id == payload.source_id,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already subscribed to this source")

    # Create subscription
    user_source = UserSources(
        user_id=current_user.id,
        source_id=payload.source_id,
    )
    db.add(user_source)
    await db.commit()
    await db.refresh(user_source)
    return UserSourceRead.model_validate(user_source)


@router.get("/", response_model=list[UserSourceRead])
async def list_user_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserSourceRead]:
    res = await db.execute(
        select(UserSources).where(UserSources.user_id == current_user.id)
    )
    items = res.scalars().all()
    return [UserSourceRead.model_validate(item) for item in items]