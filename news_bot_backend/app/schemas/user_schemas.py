from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    scan_period: int | None = 3


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserReturn(UserBase):
    id: int
    is_verified: bool | None = None
    is_super: bool | None = None

    model_config = {"from_attributes": True}


class ProfileRead(BaseModel):
    id: int
    email: str
    username: str
    first_name: str | None = None
    last_name: str | None = None
    scan_period: int = 3
    profile_photo: str | None = None
    is_verified: bool
    is_super: bool | None = None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    username: str
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    scan_period: int | None = None

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
