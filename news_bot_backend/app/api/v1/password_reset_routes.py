from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.db.database import get_db
from app.models import User
from app.schemas.password_reset import PasswordResetResponse, PasswordResetRequest, PasswordReset
from app.services.dependencies import logger, get_current_user
from app.services.email_service import send_password_reset_email
from app.services.security import create_password_reset_token, decode_token, hash_password

router = APIRouter(tags=["Password recovery"])


@router.post("/forgot-password/", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
async def forgot_password(
        request: PasswordResetRequest,
        db: AsyncSession = Depends(get_db)
):
    logger.info(f"Password reset requested for email: {request.email}")

    res=await db.execute(select(User).where(User.email == request.email))
    user=res.scalar_one_or_none()

    if user:
        try:
            reset_token = create_password_reset_token(user.id, user.email)

            email_sent = await send_password_reset_email(
                email=user.email,
                username=user.username,
                reset_token=reset_token
            )

            if email_sent:
                logger.info(f"Password reset email sent to {user.email}")
            else:
                logger.error(f"Failed to send password reset email to {user.email}")
        except Exception as e:
            logger.error(f"Error processing password reset request: {str(e)}")

    return PasswordResetResponse(
        detail="If an account with that email exists, a password reset link has been sent."
    )


@router.post("/reset-password/", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
async def reset_password(
        request: PasswordReset,
        db: AsyncSession = Depends(get_db)
):
    logger.info("Password reset attempt")

    # Decode and validate token
    payload = decode_token(request.token)

    if not payload:
        logger.warning("Invalid password reset token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Check token type
    if payload.get("type") != "password_reset":
        logger.warning("Invalid token type for password reset")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type"
        )

    # Get user ID from token
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Missing user ID in reset token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )

    # Find user
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found for password reset: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify email matches
    token_email = payload.get("email")
    if token_email != user.email:
        logger.warning(f"Email mismatch in password reset token for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )

    try:
        # Update password
        user.hashed_password = hash_password(request.new_password)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Password reset successful for user {user.id}")
        return PasswordResetResponse(
            detail="Password has been reset successfully"
        )
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting password"
        )
