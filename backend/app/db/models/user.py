"""User model — local accounts first, SSO fields reserved for P5."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import Timestamps, UUIDPrimaryKey


class User(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_users_source_external"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    handle: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    initials: Mapped[str | None] = mapped_column(String(8))
    color: Mapped[str | None] = mapped_column(String(16))

    # Profile detail (user-center page)
    title: Mapped[str | None] = mapped_column(String(120))
    department: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    timezone: Mapped[str | None] = mapped_column(String(64))
    bio: Mapped[str | None] = mapped_column(Text)

    # Auth
    password_hash: Mapped[str | None] = mapped_column(Text)  # NULL for SSO-only users
    source: Mapped[str] = mapped_column(String(16), default="local", nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    twofa_secret: Mapped[str | None] = mapped_column(Text)

    # Authorization / status
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)

    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Personal preferences memory — injected into agent context
    preferences: Mapped[dict | None] = mapped_column(JSONB, default=None)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email} role={self.role}>"
