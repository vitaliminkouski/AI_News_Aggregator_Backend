from pydantic import BaseModel


class TestBase(BaseModel):
    name: str

class TestCreate(TestBase):
    pass

class TestReturn(TestBase):
    id: int

    model_config = {"from_attributes": True}
