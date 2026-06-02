"""Async Redis client + token-blacklist helpers (for logout / device revocation)."""
from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            protocol=2,            # RESP2: fixes xreadgroup block-timeout under RESP3
            socket_timeout=10,      # generous socket timeout for blocking reads
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


# ── Refresh-token blacklist (revocation) ──
_BLACKLIST_PREFIX = "jwt:blacklist:"


async def blacklist_jti(jti: str, ttl_seconds: int) -> None:
    await get_redis().set(f"{_BLACKLIST_PREFIX}{jti}", "1", ex=max(ttl_seconds, 1))


async def is_blacklisted(jti: str) -> bool:
    return bool(await get_redis().exists(f"{_BLACKLIST_PREFIX}{jti}"))


# ── ACP prompt queue (Redis Stream) + live event channel (Pub/Sub) ──
import json as _json  # noqa: E402

from app.config import settings  # noqa: E402


def conv_channel(conversation_id: str) -> str:
    return f"chan:conv:{conversation_id}"


def cancel_key(conversation_id: str) -> str:
    return f"acp:cancel:{conversation_id}"


async def enqueue_prompt(payload: dict) -> str:
    """Push a prompt task onto the runner's Redis Stream. Returns entry id."""
    return await get_redis().xadd(settings.acp_stream, {"data": _json.dumps(payload)})


async def publish_event(conversation_id: str, event: dict) -> None:
    """Publish a streaming event to the conversation's live channel (hot path)."""
    await get_redis().publish(conv_channel(conversation_id), _json.dumps(event))


async def request_cancel(conversation_id: str) -> None:
    await get_redis().set(cancel_key(conversation_id), "1", ex=120)


async def is_cancelled(conversation_id: str) -> bool:
    return bool(await get_redis().exists(cancel_key(conversation_id)))


async def clear_cancel(conversation_id: str) -> None:
    await get_redis().delete(cancel_key(conversation_id))


# ── AI Confirmation requests ──
import asyncio as _asyncio  # noqa: E402


def confirm_key(conversation_id: str, request_id: str) -> str:
    return f"confirm:{conversation_id}:{request_id}"


async def wait_for_confirmation(conversation_id: str, request_id: str, timeout: int = 300) -> dict:
    key = confirm_key(conversation_id, request_id)
    for _ in range(timeout * 2):
        val = await get_redis().get(key)
        if val:
            await get_redis().delete(key)
            return _json.loads(val)
        await _asyncio.sleep(0.5)
    return {"choice": "deny"}


async def respond_to_confirmation(conversation_id: str, request_id: str, choice: str) -> None:
    key = confirm_key(conversation_id, request_id)
    await get_redis().set(key, _json.dumps({"choice": choice}), ex=300)
