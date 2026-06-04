"""User presence (online/offline) API.

Frontend calls POST /presence/heartbeat every 30s.
Backend stores presence in Redis with 60s TTL.
GET /presence returns batch status for requested user IDs.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.redis import presence_heartbeat, presence_status
from app.db.models.user import User
from app.deps import get_current_user

router = APIRouter()


class PresenceHeartbeatOut(BaseModel):
    ok: bool = True


class PresenceQuery(BaseModel):
    user_ids: list[str]


class PresenceResult(BaseModel):
    statuses: dict[str, str]


@router.post("/presence/heartbeat", response_model=PresenceHeartbeatOut)
async def heartbeat(user: User = Depends(get_current_user)):
    """Refresh current user's online presence. Call every ~30s."""
    await presence_heartbeat(str(user.id))
    return PresenceHeartbeatOut()


@router.post("/presence/query", response_model=PresenceResult)
async def query_presence(
    payload: PresenceQuery,
    user: User = Depends(get_current_user),
):
    """Batch query online/offline status for a list of user IDs."""
    # Validate UUIDs
    valid_ids = []
    for uid in payload.user_ids:
        try:
            uuid.UUID(uid)
            valid_ids.append(uid)
        except ValueError:
            pass
    statuses = await presence_status(valid_ids)
    return PresenceResult(statuses=statuses)
