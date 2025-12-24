from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration for the ML microservice."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    APP_NAME: str = "NewsAgent ML Service"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Model identifiers can point to a Hugging Face repo id or a local path.
    SUMMARIZATION_MODEL_NAME: str = Field(
        default="sshleifer/distilbart-cnn-12-6",
        description="Model id/path for abstractive summarisation.",
    )
    SENTIMENT_MODEL_NAME: str = Field(
        default="cointegrated/rubert-tiny",
        description="Model id/path for sentiment analysis.",
    )
    NER_MODEL_NAME: str = Field(
        default="dslim/bert-base-NER",
        description="Model id/path for named entity recognition.",
    )

    # Some models require additional kwargs (tokenizer, revision, etc.).
    SUMMARIZATION_MODEL_REVISION: Optional[str] = None
    SENTIMENT_MODEL_REVISION: Optional[str] = None
    NER_MODEL_REVISION: Optional[str] = None

    # Runtime execution
    TORCH_DEVICE: Literal["cpu", "cuda", "cuda:0"] = "cpu"
    MAX_SUMMARY_TOKENS: int = Field(default=180, ge=32, le=512)
    MIN_SUMMARY_TOKENS: int = Field(default=48, ge=8, le=256)

    # Inference knobs
    SUMMARIZATION_NUM_BEAMS: int = Field(default=4, ge=1, le=8)
    SUMMARY_LENGTH_PENALTY: float = 1.0

    LOGGER_NAME: str = "newsagent.ml"

    # Remote LLaMA/OpenAI-compatible summarization
    LLAMA_API_BASE: Optional[str] = Field(
        default=None,
        description="Base URL for LLaMA/OpenAI-compatible API (e.g., https://api.ollama.com).",
    )
    LLAMA_API_KEY: Optional[str] = Field(default=None, description="API key for hosted LLaMA provider.")
    LLAMA_MODEL: Optional[str] = Field(
        default=None,
        description="Model id for hosted summarization (e.g., llama3.2 or meta-llama/Llama-3.1-8B-Instruct).",
    )
    LLAMA_MAX_TOKENS: int = Field(default=256, ge=32, le=1024)
    LLAMA_TEMPERATURE: float = Field(default=0.2, ge=0.0, le=1.0)

    def pipeline_device(self) -> int:
        """Return device index expected by transformers' pipeline."""
        if self.TORCH_DEVICE.startswith("cuda"):
            return 0
        return -1

    def remote_llama_enabled(self) -> bool:
        return bool(self.LLAMA_API_BASE and self.LLAMA_API_KEY and self.LLAMA_MODEL)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance usable as a FastAPI dependency."""
    return Settings()
