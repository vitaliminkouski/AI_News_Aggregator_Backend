from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.db.database import get_db
from app.models import User
from app.services.dependencies import logger, get_current_user
from app.services.email_service import send_verification_email
from app.services.security import decode_token, settings
from app.services.security import create_email_verification_token

router = APIRouter(prefix="/verify-email", tags=["Email-verification"])


from sqlalchemy import select
from app.services.security import decode_token, create_email_verification_token
from app.services.email_service import send_email
from app.models import User

@router.get("/")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    creds_error = HTTPException(status_code=400, detail="Invalid or expired verification token")

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
        raise HTTPException(status_code=404, detail="User not found")

    if user.email != email:
        raise creds_error

    if user.is_verified:
        return {"message": "Email already verified", "verified": True}

    user.is_verified = True
    await db.commit()
    await db.refresh(user)
    return {"message": "Email successfully verified", "verified": True}


@router.post("/resend-verification/")
async def resend_verification_email(user: User = Depends(get_current_user),
                                    db: AsyncSession = Depends(get_db)):

    if user.is_verified:
        return {"message": "Email is already verified"}

    token = create_email_verification_token(user.id, user.email)
    link = f"{settings.BACKEND_URL}/api/v1/verify-email/?token={token}"
    subject = f"Verify your {settings.APP_NAME} account"
    html = f"""
    <p>Hello {user.username},</p>
    <p>Please verify your email by clicking <a href="{link}">this link</a>.</p>
    <p>If the button doesn't work, copy this URL: {link}</p>
    """
    sent = await send_email(user.email, subject, html)
    if sent:
        return {"message": "Verification email sent"}
    raise HTTPException(status_code=500, detail="Failed to send verification email")