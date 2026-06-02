"""Tenant system settings access."""
from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.system import DEFAULT_SETTINGS, SystemSettings


async def get(db: AsyncSession) -> SystemSettings:
    s = await db.get(SystemSettings, 1)
    if s is None:
        s = SystemSettings(id=1, data=dict(DEFAULT_SETTINGS))
        db.add(s)
        await db.commit()
        await db.refresh(s)
    # self-heal any legacy double-encoded value
    if isinstance(s.data, str):
        s.data = json.loads(s.data)
        await db.commit()
        await db.refresh(s)
    return s


async def update(db: AsyncSession, data: dict) -> SystemSettings:
    s = await get(db)
    s.data = data
    await db.commit()
    await db.refresh(s)
    return s
