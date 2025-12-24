import asyncio
import logging
from dataclasses import dataclass
from functools import partial
from typing import Any, Dict, List, Optional

import httpx
from transformers import pipeline

from app.core.config import Settings


@dataclass
class SentimentLabel:
    label: str
    score: float


@dataclass
class Entity:
    text: str
    type: str
    score: float


class TextAnalyticsService:
    """Wraps Hugging Face pipelines behind async-friendly methods."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger(settings.LOGGER_NAME)

        self._summarizer = None
        self._sentiment = None
        self._ner = None

        self._summarizer_lock = asyncio.Lock()
        self._sentiment_lock = asyncio.Lock()
        self._ner_lock = asyncio.Lock()

    async def summarize(self, text: str, *, min_tokens: Optional[int] = None, max_tokens: Optional[int] = None) -> str:
        """Generate abstractive summary for the provided text."""
        # Prefer hosted LLaMA/OpenAI-compatible endpoint if configured.
        if self.settings.remote_llama_enabled():
            try:
                summary = await self._remote_llama_summarize(text)
                if summary:
                    return summary
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.warning("Remote LLaMA summarization failed, using lightweight fallback: %s", exc)
                return self._fallback_summary(text)

        summarizer = await self._get_summarizer()
        max_tokens = max_tokens or self.settings.MAX_SUMMARY_TOKENS
        min_tokens = min_tokens or self.settings.MIN_SUMMARY_TOKENS
        self.logger.debug("Running local summarization (min=%s, max=%s)", min_tokens, max_tokens)

        result = await asyncio.to_thread(
            partial(
                summarizer,
                text,
                truncation=True,
                max_length=max_tokens,
                min_length=min_tokens,
                num_beams=self.settings.SUMMARIZATION_NUM_BEAMS,
                length_penalty=self.settings.SUMMARY_LENGTH_PENALTY,
            )
        )
        summary = result[0]["summary_text"].strip()
        self.logger.debug("Generated summary length=%s", len(summary))
        return summary

    async def sentiment(self, text: str) -> SentimentLabel:
        """Predict sentiment label and score."""
        classifier = await self._get_sentiment()
        self.logger.debug("Running sentiment analysis")
        outputs = await asyncio.to_thread(partial(classifier, text, truncation=True, top_k=1))
        # Normalise possible shapes: [{"label": "...", "score": ...}] or [[{...}]]
        if isinstance(outputs, list) and outputs:
            first = outputs[0]
            if isinstance(first, list) and first:
                first = first[0]
            if isinstance(first, dict) and "label" in first and "score" in first:
                return SentimentLabel(label=first["label"], score=float(first["score"]))
        raise RuntimeError(f"Unexpected sentiment output format: {outputs}")

    async def ner(self, text: str) -> List[Entity]:
        """Extract named entities."""
        recognizer = await self._get_ner()
        self.logger.debug("Running NER")
        outputs = await asyncio.to_thread(partial(recognizer, text, aggregation_strategy="simple"))
        return [
            Entity(text=chunk["word"], type=chunk["entity_group"], score=float(chunk["score"]))
            for chunk in outputs
        ]

    async def full_analysis(self, text: str, *, min_tokens: Optional[int] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Convenience helper that runs all models sequentially."""
        summary, sentiment, entities = await asyncio.gather(
            self.summarize(text, min_tokens=min_tokens, max_tokens=max_tokens),
            self.sentiment(text),
            self.ner(text),
        )
        return {
            "summary": summary,
            "sentiment": sentiment,
            "entities": entities,
        }

    async def _remote_llama_summarize(self, text: str) -> str:
        """Call Ollama Cloud /api/generate (non-stream) for summarization."""
        url = f"{self.settings.LLAMA_API_BASE.rstrip('/')}/generate"
        headers = {
            "Authorization": f"Bearer {self.settings.LLAMA_API_KEY}",
            "Content-Type": "application/json",
        }
        prompt = (
            "Сделай краткое фактологичное саммари новости на русском: 2–4 короткие фразы. "
            "Не выдумывай факты, обязательно сохрани числа, даты, проценты. "
            "Без Markdown и звёздочек, без заголовков и слов типа 'Краткое содержание'. "
            "Просто чистый текст с итогом новости. "
            f"Текст:\n{text}"
        )
        payload = {
            "model": self.settings.LLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.settings.LLAMA_TEMPERATURE,
                "num_predict": self.settings.LLAMA_MAX_TOKENS,
            },
        }

        self.logger.debug("Calling remote LLaMA summarization via %s", url)
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        content = (data.get("response") or "").strip()
        if not content:
            raise RuntimeError("Empty summary from remote LLaMA API")
        return content

    def _fallback_summary(self, text: str) -> str:
        """Simple fallback to avoid heavy local model load if remote is unavailable."""
        if len(text) <= 400:
            return text
        return text[:400].rstrip() + "..."

    async def _get_summarizer(self):
        if self._summarizer is None:
            async with self._summarizer_lock:
                if self._summarizer is None:
                    self.logger.info("Loading summarization pipeline: %s", self.settings.SUMMARIZATION_MODEL_NAME)
                    self._summarizer = await asyncio.to_thread(
                        pipeline,
                        "summarization",
                        model=self.settings.SUMMARIZATION_MODEL_NAME,
                        revision=self.settings.SUMMARIZATION_MODEL_REVISION,
                        device=self.settings.pipeline_device(),
                    )
        return self._summarizer

    async def _get_sentiment(self):
        if self._sentiment is None:
            async with self._sentiment_lock:
                if self._sentiment is None:
                    self.logger.info("Loading sentiment pipeline: %s", self.settings.SENTIMENT_MODEL_NAME)
                    self._sentiment = await asyncio.to_thread(
                        pipeline,
                        "text-classification",
                        model=self.settings.SENTIMENT_MODEL_NAME,
                        revision=self.settings.SENTIMENT_MODEL_REVISION,
                        device=self.settings.pipeline_device(),
                        return_all_scores=True,
                    )
        return self._sentiment

    async def _get_ner(self):
        if self._ner is None:
            async with self._ner_lock:
                if self._ner is None:
                    self.logger.info("Loading NER pipeline: %s", self.settings.NER_MODEL_NAME)
                    self._ner = await asyncio.to_thread(
                        pipeline,
                        "token-classification",
                        model=self.settings.NER_MODEL_NAME,
                        revision=self.settings.NER_MODEL_REVISION,
                        device=self.settings.pipeline_device(),
                        aggregation_strategy="simple",
                    )
        return self._ner
