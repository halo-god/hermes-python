"""Analytics: usage stats and metrics."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, Message
from app.db.models.user import User
from app.deps import get_current_user, get_db

router = APIRouter()


class DayCount(BaseModel):
    date: str
    count: int


class AgentCount(BaseModel):
    agent_id: str
    count: int


class UsageStats(BaseModel):
    total_messages: int
    total_conversations: int
    tokens_total: int
    messages_by_day: list[DayCount]
    messages_by_role: dict[str, int]
    top_agents: list[AgentCount]


@router.get("/analytics/usage", response_model=UsageStats)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated usage statistics for the current user."""
    uid = user.id
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # Total counts
    total_msgs = (
        await db.execute(
            select(func.count()).select_from(Message).where(Message.owner_id == uid)
        )
    ).scalar() or 0

    total_convos = (
        await db.execute(
            select(func.count()).select_from(Conversation).where(Conversation.owner_id == uid)
        )
    ).scalar() or 0

    # Token totals
    tokens_in = (
        await db.execute(
            select(func.coalesce(func.sum(Message.tokens_in), 0)).where(
                Message.owner_id == uid
            )
        )
    ).scalar() or 0
    tokens_out = (
        await db.execute(
            select(func.coalesce(func.sum(Message.tokens_out), 0)).where(
                Message.owner_id == uid
            )
        )
    ).scalar() or 0

    # Messages by day (last 30 days)
    day_rows = (
        await db.execute(
            select(
                func.date_trunc("day", Message.created_at).label("day"),
                func.count().label("cnt"),
            )
            .where(Message.owner_id == uid, Message.created_at >= thirty_days_ago)
            .group_by("day")
            .order_by("day")
        )
    ).all()

    messages_by_day = [
        DayCount(date=r.day.strftime("%Y-%m-%d"), count=r.cnt) for r in day_rows
    ]

    # Messages by role
    role_rows = (
        await db.execute(
            select(Message.role, func.count().label("cnt"))
            .where(Message.owner_id == uid)
            .group_by(Message.role)
        )
    ).all()
    messages_by_role = {r.role: r.cnt for r in role_rows}

    # Top agents
    agent_rows = (
        await db.execute(
            select(Message.agent_id, func.count().label("cnt"))
            .where(Message.owner_id == uid, Message.agent_id.isnot(None))
            .group_by(Message.agent_id)
            .order_by(func.count().desc())
            .limit(5)
        )
    ).all()
    top_agents = [AgentCount(agent_id=r.agent_id, count=r.cnt) for r in agent_rows]

    return UsageStats(
        total_messages=total_msgs,
        total_conversations=total_convos,
        tokens_total=tokens_in + tokens_out,
        messages_by_day=messages_by_day,
        messages_by_role=messages_by_role,
        top_agents=top_agents,
    )
