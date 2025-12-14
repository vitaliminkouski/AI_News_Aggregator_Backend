import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, Form
from fastapi.params import Depends, File
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models import User
from app.schemas.user_schemas import UserReturn
from app.services.email_service import send_verification_email
from app.services.security import hash_password, create_email_verification_token

logger=get_logger(__name__)
router = APIRouter()

settings=get_settings()


@router.post("/register/", response_model=UserReturn, status_code=status.HTTP_201_CREATED)
async def register_user(
        username: str = Form(...),
        email: EmailStr = Form(...),
        first_name: str = Form(None),
        last_name: str = Form(None),
        scan_period: int = Form(3),
        password: str = Form(min_length=8),
        profile_photo: UploadFile | None = File(None),
        db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(f"Registration attempt for username {username}")
        user = await db.execute(select(User).where(
            (User.username == username) | (User.email == email)))

        if user.scalar_one_or_none():
            logger.warning(f"Registration failed: username or email already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )

        # Save profile photo
        if profile_photo is not None:
            file_extension = Path(profile_photo.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = f"{settings.PROFILE_PHOTOS_DIR}/{unique_filename}"

            try:
                Path(settings.PROFILE_PHOTOS_DIR).mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(file_path, "wb") as f:
                    while contents := await profile_photo.read(1024 * 1024):
                        await f.write(contents)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"There was an error uploading the file: {e}"
                )
        else:
            file_path = ""

        # Create user in db
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            scan_period=scan_period,
            profile_photo=file_path,
            hashed_password=hash_password(password),
            is_verified=False  # User starts unverified
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Generate verification token and send email
        verification_token = create_email_verification_token(user.id, email)
        email_sent = await send_verification_email(email, username, verification_token)

        if not email_sent:
            logger.warning(f"Failed to send verification email to {email}, but user was created")

        logger.info(f"User {user.username} successfully registered")

        return UserReturn(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            scan_period=user.scan_period,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Something went wrong: {str(e)}"
        )



