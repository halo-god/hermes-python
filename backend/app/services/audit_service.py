"""Audit recording + querying."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import async_session_maker
from app.db.models.audit import AuditLog


async def record(
    *,
    action: str,
    actor_id=None,
    actor_name: str | None = None,
    target: str | None = None,
    ip: str | None = None,
    result: str = "ok",
    meta: dict | None = None,
    db: AsyncSession | None = None,
) -> None:
    """Append an audit entry. Uses its own session unless one is passed."""
    entry = AuditLog(
        action=action,
        actor_id=actor_id,
        actor_name=actor_name,
        target=target,
        ip=ip,
        result=result,
        meta=meta or {},
    )
    if db is not None:
        db.add(entry)
        await db.flush()
        return
    async with async_session_maker() as s:
        s.add(entry)
        await s.commit()


async def query(
    db: AsyncSession,
    *,
    action: str | None = None,
    result: str | None = None,
    limit: int = 100,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[AuditLog]:
    from datetime import timezone
    stmt = select(AuditLog).order_by(AuditLog.ts.desc()).limit(min(limit, 500))
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if result:
        stmt = stmt.where(AuditLog.result == result)
    if date_from:
        try:
            from datetime import datetime
            dt = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            stmt = stmt.where(AuditLog.ts >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import datetime, timedelta
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            stmt = stmt.where(AuditLog.ts < dt)
        except ValueError:
            pass
    res = await db.execute(stmt)
    return list(res.scalars().all())
