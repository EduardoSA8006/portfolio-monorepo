from pydantic import BaseModel, EmailStr, Field, field_validator

from app.shared.security import is_strong_password


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=200)
    password: str = Field(..., min_length=8)


class AdminUserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr = Field(..., max_length=200)
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not is_strong_password(v):
            raise ValueError(
                "Password must be at least 8 characters and contain uppercase, "
                "lowercase, digit, and special character"
            )
        return v


class AdminUserResponse(BaseModel):
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    csrf_token: str
    message: str = "Login successful"
