from datetime import datetime
from pydantic import BaseModel

class UserSourceCreate(BaseModel):
    source_id: int

class UserSourceRead(BaseModel):
    id: int
    user_id: int
    source_id: int
    subscribed_at: datetime

    model_config = {"from_attributes": True}