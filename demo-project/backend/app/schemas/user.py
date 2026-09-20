from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

class UserBase(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN, description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="member", pattern="^(admin|manager|member)$")
    is_active: bool = True

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, pattern=EMAIL_PATTERN)
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, pattern="^(admin|manager|member)$")
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
