import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, File
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models import User
from app.schemas.user_schemas import ProfileRead, ProfileUpdate
from app.services.dependencies import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/profile", tags=["profile"])

settings = get_settings()


@router.get("/", response_model=ProfileRead)
async def get_profile(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
) -> ProfileRead:



    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    logger.info(f"Profile retrieved for user {user.id}")
    return ProfileRead(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_super=user.is_super,
        is_verified=user.is_verified,
        scan_period=user.scan_period,
        profile_photo=user.profile_photo
    )


@router.patch("/", response_model=ProfileRead)
async def update_profile(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
        email: EmailStr | None = Form(None),
        first_name: str | None = Form(None),
        last_name: str | None = Form(None),
        scan_period: int | None = Form(None),
        profile_photo: UploadFile | None = File(None)
) -> ProfileRead:


    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    try:
        # Update email if provided and check for duplicates
        if email is not None and email != user.email:
            existing_user = await db.execute(
                select(User).where(User.email == email, User.id != user_id)
            )
            if existing_user.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
            user.email = email

        # Update other fields if provided
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if scan_period is not None:
            user.scan_period = scan_period

        # Handle profile photo upload
        if profile_photo is not None:
            # Delete old photo if exists
            if user.profile_photo:
                old_photo_path = Path(user.profile_photo)
                if old_photo_path.exists():
                    try:
                        old_photo_path.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to delete old profile photo: {e}")

            # Save new photo
            file_extension = Path(profile_photo.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = f"{settings.PROFILE_PHOTOS_DIR}/{unique_filename}"

            try:
                Path(settings.PROFILE_PHOTOS_DIR).mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(file_path, "wb") as f:
                    while contents := await profile_photo.read(1024 * 1024):
                        await f.write(contents)
                user.profile_photo = file_path
            except Exception as e:
                logger.error(f"Error uploading profile photo: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error uploading profile photo: {str(e)}"
                )

        await db.commit()
        await db.refresh(user)

        logger.info(f"Profile updated for user {user.id}")

        return ProfileRead(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_super=user.is_super,
            scan_period=user.scan_period,
            profile_photo=user.profile_photo
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )