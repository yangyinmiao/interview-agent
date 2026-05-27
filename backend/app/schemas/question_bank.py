from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class QuestionBankCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None


class QuestionBankResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    question: str
    answer: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    difficulty: str = "medium"


class QuestionResponse(BaseModel):
    id: str
    question: str
    answer: Optional[str] = None
    tags: list[str]
    difficulty: str
