"""Pydantic schemas for authentication."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class TokenData(BaseModel):
    user_id: int | None = None
    role: str | None = None


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(default="patient", pattern="^(patient|doctor)$")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True
