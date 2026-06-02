"""User persistence + helpers."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User
from app.schemas.user import UserCreate


def _initials(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "?"
    # CJK: take first char; latin: take initials of first two words.
    if any("一" <= ch <= "鿿" for ch in name):
        return name[0]
    parts = name.split()
    return ("".join(p[0] for p in parts[:2])).upper() or name[0].upper()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    res = await db.execute(select(User).where(User.email == email.lower()))
    return res.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(
        email=str(data.email).lower(),
        name=data.name,
        handle=data.handle,
        title=data.title,
        department=data.department,
        phone=data.phone,
        timezone=data.timezone,
        bio=data.bio,
        color=data.color or "#b8852a",
        initials=_initials(data.name),
        password_hash=hash_password(data.password),
        source="local",
        role=data.role,
        status="active",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
