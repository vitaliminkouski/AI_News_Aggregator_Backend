import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, File
from fastapi.responses import FileResponse
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


def _get_photo_url(photo_path: str | None) -> str | None:
    if not photo_path:
        return None
    
    base_url = settings.BACKEND_URL.replace('/api/v1', '')
    
    # If path already starts with /static/, use as is
    if photo_path.startswith("/static/"):
        return f"{base_url}{photo_path}"
    
    # If path starts with static/ (without leading slash), add leading slash
    if photo_path.startswith("static/"):
        return f"{base_url}/{photo_path}"
    
    # Otherwise, construct URL from path
    return f"{base_url}/static/{photo_path}"


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
    
    # Convert photo path to full URL
    photo_url = _get_photo_url(user.profile_photo)
    
    return ProfileRead(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_super=user.is_super,
        is_verified=user.is_verified,
        scan_period=user.scan_period,
        profile_photo=photo_url
    )


@router.get("/photo")
async def get_profile_photo(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Get profile photo as image file."""
    if not user or not user.profile_photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile photo not found"
        )
    
    photo_path = Path(user.profile_photo)
    
    # If path is relative, construct full path
    if not photo_path.is_absolute():
        photo_path = Path(settings.PROFILE_PHOTOS_DIR) / photo_path.name
    
    if not photo_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile photo file not found"
        )
    
    return FileResponse(
        path=str(photo_path),
        media_type="image/jpeg"  # Adjust based on your file types
    )


@router.patch("/", response_model=ProfileRead)
async def update_profile(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
        email: EmailStr | None = Form(None),
        first_name: str | None = Form(None),
        last_name: str | None = Form(None),
        scan_period: int | None = Form(None),
        delete_photo: bool = Form(False),
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
                select(User).where(User.email == email, User.id != user.id)
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

        # Handle profile photo deletion
        if delete_photo:
            if user.profile_photo:
                photo_path = Path(user.profile_photo)
                # If path is relative, construct full path
                if not photo_path.is_absolute():
                    photo_path = Path(settings.PROFILE_PHOTOS_DIR) / photo_path.name
                
                if photo_path.exists():
                    try:
                        photo_path.unlink()
                        logger.info(f"Deleted profile photo file for user {user.id}")
                    except Exception as e:
                        logger.warning(f"Failed to delete profile photo file for user {user.id}: {e}")
                
                user.profile_photo = None
                logger.info(f"Profile photo deleted for user {user.id}")

        # Handle profile photo upload (only if not deleting)
        elif profile_photo is not None:
            # Delete old photo if exists
            if user.profile_photo:
                old_photo_path = Path(user.profile_photo)
                # If path is relative, construct full path
                if not old_photo_path.is_absolute():
                    old_photo_path = Path(settings.PROFILE_PHOTOS_DIR) / old_photo_path.name
                
                if old_photo_path.exists():
                    try:
                        old_photo_path.unlink()
                        logger.info(f"Deleted old profile photo for user {user.id}")
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
                logger.info(f"Uploaded new profile photo for user {user.id}")
            except Exception as e:
                logger.error(f"Error uploading profile photo: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error uploading profile photo: {str(e)}"
                )

        await db.commit()
        await db.refresh(user)

        logger.info(f"Profile updated for user {user.id}")

        # Convert photo path to full URL
        photo_url = _get_photo_url(user.profile_photo)

        return ProfileRead(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_super=user.is_super,
            is_verified=user.is_verified,  # Добавьте эту строку
            scan_period=user.scan_period,
            profile_photo=photo_url
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


@router.delete("/", status_code=status.HTTP_200_OK)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    try:
        user_id = user.id
        username = user.username
        
        # Delete profile photo if exists
        if user.profile_photo:
            photo_path = Path(user.profile_photo)
            # If path is relative, construct full path
            if not photo_path.is_absolute():
                photo_path = Path(settings.PROFILE_PHOTOS_DIR) / photo_path.name
            
            if photo_path.exists():
                try:
                    photo_path.unlink()
                    logger.info(f"Deleted profile photo for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete profile photo for user {user_id}: {e}")


        await db.delete(user)
        await db.commit()

        logger.info(f"Account deleted for user {user_id} (username: {username})")
        
        return {
            "message": "Account successfully deleted",
            "deleted_user_id": user_id
        }

    except Exception as e:
        logger.error(f"Error deleting account for user {user.id}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting account: {str(e)}"
        )