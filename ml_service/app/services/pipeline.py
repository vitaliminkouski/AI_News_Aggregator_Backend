import asyncio
import logging
from dataclasses import dataclass
from functools import partial
from typing import Any, Dict, List, Optional

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
        summarizer = await self._get_summarizer()
        max_tokens = max_tokens or self.settings.MAX_SUMMARY_TOKENS
        min_tokens = min_tokens or self.settings.MIN_SUMMARY_TOKENS
        self.logger.debug("Running summarization (min=%s, max=%s)", min_tokens, max_tokens)

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
        outputs = await asyncio.to_thread(partial(classifier, text, truncation=True, top_k=None))
        # Most models return list of dicts sorted by score desc; take top-1.
        top = max(outputs[0], key=lambda item: item["score"])
        return SentimentLabel(label=top["label"], score=float(top["score"]))

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

