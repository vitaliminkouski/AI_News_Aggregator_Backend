from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models import User
from app.services.security import decode_token

logger = get_logger(__name__)

# Make OAuth2 optional (for Swagger OAuth2 flow)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/", auto_error=False)
# Make HTTPBearer primary (for manual token entry)
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
        http_credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
        token: Optional[str] = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
):
    """Get current user from either Bearer token or OAuth2 token."""
    # Try Bearer token first (for manual entry in Swagger)
    actual_token = None

    if http_credentials:
        actual_token = http_credentials.credentials
    elif token:
        actual_token = token

    if not actual_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(actual_token)

    if payload is None:
        logger.error("Invalid token")
        raise credentials_exception

    user_id: str = payload.get("sub")
    token_type: str = payload.get("type")

    if user_id is None or token_type != "access":
        logger.error("Invalid token")
        raise credentials_exception

    try:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if user is None:
            logger.error("Invalid token")
            raise credentials_exception
        return user
    except HTTPException:
        raise

    except:
        logger.error("Error during access database")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during access database"
        )


async def get_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_super:
        logger.warning(f"User {current_user.id} attempted to access superuser-only endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    return current_user