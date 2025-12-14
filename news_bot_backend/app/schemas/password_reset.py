from pydantic import BaseModel, EmailStr, Field


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class PasswordResetResponse(BaseModel):
    detail: str
