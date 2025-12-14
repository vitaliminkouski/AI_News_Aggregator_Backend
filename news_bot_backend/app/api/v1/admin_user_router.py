from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models import User
from app.schemas.user_schemas import UserCreate, UserReturn
from app.services.dependencies import get_superuser
from app.services.security import hash_password

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

@router.get("/", response_model=list[UserReturn])
async def list_users_admin(
    db: AsyncSession = Depends(get_db),
    superuser: User = Depends(get_superuser),
):
    res = await db.execute(select(User))
    users = res.scalars().all()
    return [UserReturn.model_validate(u) for u in users]

@router.post("/", response_model=UserReturn, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    superuser: User = Depends(get_superuser),
):
    # Uniqueness checks
    existing = await db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        scan_period=payload.scan_period or 3,
        hashed_password=hash_password(payload.password),
        is_verified=True,   # optional: mark verified
        is_super=False,     # optional: change to True if you want to create superusers
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserReturn.model_validate(user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    superuser: User = Depends(get_superuser),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Optional: prevent self-delete
    if user.id == superuser.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    await db.delete(user)
    await db.commit()