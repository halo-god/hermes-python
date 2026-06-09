"""Agent memory endpoints — per-user notes, user_profile, soul."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models.user import User
from app.deps import get_current_user
from app.services import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryOut(BaseModel):
    notes: str | None
    user_profile: str | None
    soul: str | None


class MemoryUpdate(BaseModel):
    notes: str | None = None
    user_profile: str | None = None
    soul: str | None = None


@router.get("", response_model=MemoryOut)
async def get_memory(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemoryOut:
    mem = await memory_service.get_memory(db, user.id)
    if mem is None:
        return MemoryOut(notes=None, user_profile=None, soul=None)
    return MemoryOut(notes=mem.notes, user_profile=mem.user_profile, soul=mem.soul)


@router.put("", response_model=MemoryOut)
async def update_memory(
    payload: MemoryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemoryOut:
    mem = await memory_service.upsert_memory(
        db,
        user.id,
        notes=payload.notes,
        user_profile=payload.user_profile,
        soul=payload.soul,
    )
    return MemoryOut(notes=mem.notes, user_profile=mem.user_profile, soul=mem.soul)
