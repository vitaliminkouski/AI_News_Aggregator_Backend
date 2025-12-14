from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models import User
from app.services.dependencies import get_current_user
from app.services.email_service import send_email
from app.services.security import decode_token, create_email_verification_token

router = APIRouter(prefix="/verify-email", tags=["Email-verification"])

logger = get_logger(__name__)
settings = get_settings()


@router.get("/")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify user's email address using verification token."""
    creds_error = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired verification token"
    )

    payload = decode_token(token)
    if not payload or payload.get("type") != "email_verification":
        raise creds_error

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise creds_error

    res = await db.execute(select(User).where(User.id == int(user_id)))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.email != email:
        raise creds_error

    if user.is_verified:
        return {"message": "Email already verified", "verified": True}

    user.is_verified = True
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"Email verified for user {user.username} (ID: {user.id})")
    return {"message": "Email successfully verified", "verified": True}


@router.post("/resend-verification/")
async def resend_verification_email(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resend verification email to the current user."""
    if user.is_verified:
        return {"message": "Email is already verified"}

    token = create_email_verification_token(user.id, user.email)
    # BACKEND_URL already includes /api/v1, so just add /verify-email/
    link = f"{settings.BACKEND_URL}/verify-email/?token={token}"
    subject = f"Verify your {settings.APP_NAME} account"
    html = f"""
    <p>Hello {user.username},</p>
    <p>Please verify your email by clicking <a href="{link}">this link</a>.</p>
    <p>If the button doesn't work, copy this URL: {link}</p>
    <p>This link will expire in {settings.EMAIL_CONFIRM_EXPIRE_HOURS} hours.</p>
    """
    sent = await send_email(user.email, subject, html)
    if sent:
        return {"message": "Verification email sent"}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to send verification email"
    )