"""User DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    name: str
    handle: str | None = None
    title: str | None = None
    department: str | None = None
    phone: str | None = None
    timezone: str | None = None
    bio: str | None = None
    color: str | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role: str = "member"


class UserUpdate(BaseModel):
    name: str | None = None
    handle: str | None = None
    title: str | None = None
    department: str | None = None
    phone: str | None = None
    timezone: str | None = None
    bio: str | None = None
    color: str | None = None
    preferences: dict | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    initials: str | None = None
    source: str
    role: str
    status: str
    preferences: dict | None = None
    created_at: datetime
    last_active_at: datetime | None = None
