from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.source import SourceRead
from app.schemas.topic import TopicReturn


class EntityModel(BaseModel):
    text: str
    type: str
    score: float


class ArticleRead(BaseModel):
    id: int
    title: Optional[str]
    summary: Optional[str]
    content: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    published_at: Optional[datetime]
    fetched_at: datetime = None
    topic_id: Optional[int] = None
    source_id: Optional[int] = None
    sentiment_label: Optional[str]
    sentiment_score: Optional[float]
    entities: List[EntityModel] = []

    model_config = {"from_attributes": True}


class ArticleListResponse(BaseModel):
    items: List[ArticleRead]
    total: int


class IngestRequest(BaseModel):
    source_ids: Optional[List[int]] = Field(default=None, description="Subset of source IDs to ingest")
    limit: int = Field(default=10, ge=1, le=50)

