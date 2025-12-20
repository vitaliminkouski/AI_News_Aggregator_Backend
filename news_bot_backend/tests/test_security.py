# news_bot_backend/tests/test_security.py
import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt, ExpiredSignatureError

from app.services.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_jwt_token,
    decode_token,
    create_email_verification_token,
    create_password_reset_token,
)
from app.core.config import get_settings

settings = get_settings()


class TestPasswordHashing:
    """Тесты для хеширования паролей."""

    def test_hash_password(self):
        """Тест хеширования пароля."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash format

    def test_verify_password_correct(self):
        """Тест проверки правильного пароля."""
        password = "testpassword123"
        hashed = hash_password(password)  # Сначала хешируем

        # Проверяем что hash_password действительно вернул хеш
        assert hashed is not None, "hash_password returned None"
        assert isinstance(hashed, str), f"hash_password returned {type(hashed)}, expected str"
        assert hashed != password, f"hash_password returned plain password: {hashed}"
        assert hashed.startswith("$2b$"), f"hash_password returned invalid hash format: {hashed[:20]}"

        # Проверяем: передаем хеш (первый аргумент) и plain password (второй аргумент)
        # Сигнатура: verify_password(hashed_password: str, plain_password: str)
        result = verify_password(hashed, password)
        assert result is True, f"verify_password failed with hash={hashed[:20]}... and password={password}"

    def test_verify_password_incorrect(self):
        """Тест проверки неправильного пароля."""
        password = "testpassword123"
        hashed = hash_password(password)  # Сначала хешируем

        # Проверяем что hash_password действительно вернул хеш
        assert hashed is not None, "hash_password returned None"
        assert isinstance(hashed, str), f"hash_password returned {type(hashed)}, expected str"
        assert hashed != password, f"hash_password returned plain password: {hashed}"
        assert hashed.startswith("$2b$"), f"hash_password returned invalid hash format: {hashed[:20]}"

        # Передаем хеш и неправильный пароль
        result = verify_password(hashed, "wrongpassword")
        assert result is False, f"verify_password should return False for wrong password"

        # ... existing code ...

    def test_verify_password_same_password_different_hash(self):
        """Тест что один и тот же пароль дает разные хеши (из-за salt)."""
        password = "testpassword123"

        hashed1 = hash_password(password)
        hashed2 = hash_password(password)

        # Проверяем что hash_password действительно вернул хеши
        assert hashed1 is not None, "hash_password returned None for first hash"
        assert hashed2 is not None, "hash_password returned None for second hash"
        assert isinstance(hashed1, str), f"hash_password returned {type(hashed1)}, expected str"
        assert isinstance(hashed2, str), f"hash_password returned {type(hashed2)}, expected str"
        assert hashed1.startswith("$2b$"), f"hash_password returned invalid hash format: {hashed1[:20]}"
        assert hashed2.startswith("$2b$"), f"hash_password returned invalid hash format: {hashed2[:20]}"

        # Хеши должны быть разными из-за salt
        assert hashed1 != hashed2, "Two hashes of the same password should be different due to salt"

        # Но оба должны верифицироваться
        assert verify_password(hashed1, password) is True, f"First hash verification failed"
        assert verify_password(hashed2, password) is True, f"Second hash verification failed"


class TestAccessToken:
    """Тесты для access токенов."""

    def test_create_access_token(self):
        """Тест создания access токена."""
        data = {"sub": "1", "username": "testuser"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)

        # Декодируем и проверяем содержимое
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["sub"] == "1"
        assert decoded["username"] == "testuser"
        assert decoded["type"] == "access"
        assert "exp" in decoded

    def test_access_token_expiration(self):
        """Тест что токен содержит время истечения."""
        data = {"sub": "1"}
        token = create_access_token(data)

        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in decoded

        # Проверяем что exp в будущем
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        assert exp_time > datetime.now(timezone.utc)


class TestRefreshToken:
    """Тесты для refresh токенов."""

    def test_create_refresh_token(self):
        """Тест создания refresh токена."""
        data = {"sub": "1", "username": "testuser"}
        token, jti, expire = create_refresh_token(data)

        assert token is not None
        assert jti is not None
        assert expire is not None

        # Декодируем и проверяем содержимое
        decoded = verify_jwt_token(token)
        assert decoded["sub"] == "1"
        assert decoded["jti"] == str(jti)
        assert decoded["scope"] == "refresh"
        assert decoded["type"] == "refresh"

    def test_verify_refresh_token_invalid(self):
        """Тест проверки невалидного refresh токена."""
        invalid_token = "invalid.token.here"

        with pytest.raises(Exception):  # HTTPException из verify_jwt_token
            verify_jwt_token(invalid_token)


class TestEmailVerificationToken:
    """Тесты для токенов верификации email."""

    def test_create_email_verification_token(self):
        """Тест создания токена верификации email."""
        token = create_email_verification_token(user_id=1, email="test@example.com")

        assert token is not None

        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["sub"] == "1"
        assert decoded["email"] == "test@example.com"
        assert decoded["type"] == "email_verification"


class TestPasswordResetToken:
    """Тесты для токенов сброса пароля."""

    def test_create_password_reset_token(self):
        """Тест создания токена сброса пароля."""
        token = create_password_reset_token(user_id=1, email="test@example.com")

        assert token is not None

        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["sub"] == "1"
        assert decoded["email"] == "test@example.com"
        assert decoded["type"] == "password_reset"