from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
import uuid

from starlette.exceptions import HTTPException

from app.core.config import get_settings

settings = get_settings()

pwd_ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(plain_password: str):
    return pwd_ctx.hash(plain_password)


def verify_password(hashed_password: str, plain_password: str):
    return pwd_ctx.verify(hashed_password, plain_password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "expire": str(expire),
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = uuid.uuid4()
    to_encode.update(
        {
            "exp": expire,
            "jti": str(jti),
            "scope": "refresh",
            "type": "refresh"
        }
    )

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, jti, expire


def verify_jwt_token(token: str):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Refresh token is not valid"
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        if payload.get("scope") != "refresh" or \
                payload.get("sub") is None or \
                payload.get("jti") is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def decode_token(token: str):
    try:
        payload = jwt.decode(token=token, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
