from typing import List, Optional

from pydantic import BaseModel, Field

from app.services.pipeline import Entity, SentimentLabel


class SummarizationRequest(BaseModel):
    text: str = Field(..., min_length=32, description="Full article text for summarisation.")
    min_tokens: Optional[int] = Field(default=None, ge=8, le=512)
    max_tokens: Optional[int] = Field(default=None, ge=32, le=1024)


class SummarizationResponse(BaseModel):
    summary: str


class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=8, description="Text portion to analyse sentiment for.")


class SentimentResponse(BaseModel):
    label: str
    score: float

    @classmethod
    def from_dataclass(cls, data: SentimentLabel) -> "SentimentResponse":
        return cls(label=data.label, score=data.score)


class NerRequest(BaseModel):
    text: str = Field(..., min_length=8, description="Text for named entity recognition.")


class EntityModel(BaseModel):
    model_config = {"from_attributes": True}

    text: str
    type: str
    score: float


class NerResponse(BaseModel):
    entities: List[EntityModel]

    @classmethod
    def from_dataclasses(cls, items: List[Entity]) -> "NerResponse":
        return cls(entities=[EntityModel.model_validate(item) for item in items])


class FullAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=32)
    min_tokens: Optional[int] = Field(default=None, ge=8, le=512)
    max_tokens: Optional[int] = Field(default=None, ge=32, le=1024)


class FullAnalysisResponse(BaseModel):
    summary: str
    sentiment: SentimentResponse
    entities: List[EntityModel]

