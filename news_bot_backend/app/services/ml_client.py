# app/services/ml_client.py
import httpx
from app.core.logging_config import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


def _get_fallback_summary(text: str) -> str:
    """Возвращает первые 200 символов текста как fallback summary."""
    if len(text) <= 200:
        return text
    return text[:200] + "..."


async def get_summary_from_ml(text: str) -> str:
    """
    Получает summary из ML сервиса.
    Если сервис недоступен, возвращает первые 200 символов текста.
    """
    try:
        async with httpx.AsyncClient(timeout=settings.ML_TIMEOUT) as client:
            response = await client.post(
                settings.ML_SERVICE_URL,
                json={"text": text},
                timeout=settings.ML_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            summary = data.get("summary", "")

            # Если summary пустой, используем fallback
            if not summary or not summary.strip():
                logger.warning("ML Service returned empty summary, using fallback")
                return _get_fallback_summary(text)

            return summary

    except httpx.TimeoutException as e:
        logger.warning(f"ML Service timeout after {settings.ML_TIMEOUT}s, using fallback: {e}")
        return _get_fallback_summary(text)

    except httpx.ConnectError as e:
        logger.warning(f"ML Service connection error (service may be down), using fallback: {e}")
        return _get_fallback_summary(text)

    except httpx.HTTPStatusError as e:
        logger.error(
            f"ML Service HTTP error {e.response.status_code}: {e.response.text}, using fallback"
        )
        return _get_fallback_summary(text)

    except Exception as e:
        logger.error(f"ML Service unexpected error: {e}, using fallback", exc_info=True)
        return _get_fallback_summary(text)