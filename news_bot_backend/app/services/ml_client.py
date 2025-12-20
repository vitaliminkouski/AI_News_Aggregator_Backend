import httpx
from app.core.logging_config import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings=get_settings()

async def get_summary_from_ml(text: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(settings.ML_SERVICE_URL, json={"text": text})
            response.raise_for_status()
            data = response.json()
            return data.get("summary", text[:200] + "...")  # Fallback to snippet
    except Exception as e:
        logger.error(f"ML Service error: {e}")
        return text[:200] + "..."  # Fallback
