from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse

class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class CommentCreate(CommentBase):
    author_id: int

class CommentResponse(CommentBase):
    id: int
    task_id: int
    author_id: int
    author: Optional[UserResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
