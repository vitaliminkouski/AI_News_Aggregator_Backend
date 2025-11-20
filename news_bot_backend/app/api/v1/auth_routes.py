from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models import User, RefreshToken
from app.schemas.token import Token
from app.services.security import verify_password, create_access_token, create_refresh_token, hash_password, \
    decode_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)


@router.post("/login/", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(),
                db: AsyncSession = Depends(get_db)):
    logger.info("Starting log in")
    result = await db.execute(select(User).where(
        (User.username == form_data.username) | (User.email == form_data.username)
    ))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Incorrect password or username")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password or username",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token, jti, expire = create_refresh_token({"sub": str(user.id)})

    try:

        db_refresh_token = RefreshToken(
            hashed_token=refresh_token,
            jti=jti,
            user_id=user.id,
            expires_at=expire
        )
        db.add(db_refresh_token)
        await db.commit()
        await db.refresh(db_refresh_token)
        logger.info("Refresh token has been created")
        return {
            "access": access_token,
            "refresh": refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        logger.error(f"Error during creating refresh token in database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during creating refresh token in database"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token_endpoint(
        refresh_token: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    payload = decode_token(refresh_token)
    if not payload or payload.get("scope") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    jti = payload.get("jti")
    user_id = payload.get("sub")

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    stored_token = result.scalar_one_or_none()

    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    if stored_token.is_revoked:
        logger.warning("Token revoked")
        raise HTTPException(status_code=401, detail="Token revoked")

    if not verify_password(refresh_token, stored_token.hashed_token):
        logger.warning("Invalid token signature")
        raise HTTPException(status_code=401, detail="Invalid token signature")




    new_access_token = create_access_token(data={"sub": user_id})


    return {
        "access": new_access_token,
        "refresh": refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
        refresh_token: str = Form(...),
        db: AsyncSession = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token"
    )

    payload = decode_token(refresh_token)
    if not payload or payload.get("scope") != "refresh":  #
        raise credentials_exception

    jti = payload.get("jti")
    if not jti:
        logger.error("Invalid refresh token")
        raise credentials_exception

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))  #
    stored_token = result.scalar_one_or_none()

    if not stored_token:
        logger.error("Token doesn't exist in DB")
        raise credentials_exception

    if stored_token.is_revoked:
        return {"detail": "Successfully logged out"}


    if not verify_password(refresh_token, stored_token.hashed_token):  #
        raise credentials_exception

    try:
        stored_token.is_revoked = True
        await db.delete(stored_token)
        await db.commit()
    except:
        logger.error("Can't delete refresh token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Can't delete refresh token"
        )

    return {"detail": "Successfully logged out"}