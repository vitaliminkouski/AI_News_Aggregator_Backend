from pydantic import BaseModel


class TopicCreate(BaseModel):
    name: str

class TopicReturn(TopicCreate):
    id: int

    model_config = {"from_attributes": True}