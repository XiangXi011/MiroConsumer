"""认证 API 输入校验"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8)
    email: Optional[str] = Field(default=None, max_length=200)
    tenant_id: Optional[str] = None
    role: str = Field(default="viewer", pattern="^(owner|admin|researcher|viewer|auditor|service)$")


class UpdateProfileRequest(BaseModel):
    email: Optional[str] = Field(default=None, max_length=200)
    display_name: Optional[str] = Field(default=None, max_length=100)
    preferences: Optional[dict] = None


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    expires_days: int = Field(default=90, ge=1, le=365)
    permissions: Optional[list] = None
