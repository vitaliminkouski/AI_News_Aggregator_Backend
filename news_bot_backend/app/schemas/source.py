from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, AnyHttpUrl


class SourceBase(BaseModel):
    source_name: Optional[str] = Field(None, max_length=100)
    source_url: AnyHttpUrl
    language: Optional[str] = Field(default=None, max_length=5)
    topic_id: Optional[int] = None


class SourceCreate(SourceBase):
    is_active: bool = True


class SourceUpdate(BaseModel):
    source_name: Optional[str] = Field(default=None, max_length=100)
    source_url: Optional[AnyHttpUrl] = None
    language: Optional[str] = Field(default=None, max_length=5)
    topic_id: Optional[int] = None
    is_active: Optional[bool] = None


class SourceRead(SourceBase):
    id: int
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_fetched_at: Optional[datetime]

    model_config = {"from_attributes": True}
