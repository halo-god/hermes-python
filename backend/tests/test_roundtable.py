"""Roundtable multi-agent orchestration (P3).

Runs the Agent Runner in-process, sets 3 active agents, dispatches a turn, and
collects events off the Redis channel — proving parallel ACP replies (one per
agent slot) + a Hermes-synthesized merge, all persisted on one roundtable
message. (The WebSocket transport is a thin relay over this same channel.)
"""
from __future__ import annotations

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import settings
from app.core import redis as R
from app.db.base import async_session_maker
from app.main import app
from agent_runner.runner import Runner

PREFIX = settings.api_v1_prefix


async def _services_ok() -> bool:
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
        await R.get_redis().ping()
        return True
    except Exception:
        return False


@pytest.mark.asyncio
async def test_roundtable_orchestration():
    if not await _services_ok():
        pytest.skip("PostgreSQL/Redis not reachable")

    runner = Runner()
    runner_task = asyncio.create_task(runner.run())
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                f"{PREFIX}/auth/login",
                json={"method": "local", "username": settings.first_admin_email,
                      "password": settings.first_admin_password},
            )
            h = {"Authorization": f"Bearer {r.json()['access_token']}"}

            r = await c.post(f"{PREFIX}/conversations", json={"primary_agent_id": "hermes"}, headers=h)
            cid = r.json()["id"]

            # roundtable requires the mock agents — skip if discovery found <3
            agents = (await c.get(f"{PREFIX}/agents", headers=h)).json()
            ids = {a["id"] for a in agents}
            if not {"hermes", "cowork", "critic"} <= ids:
                pytest.skip("mock roundtable agents not registered (real CLI present)")

            r = await c.put(f"{PREFIX}/conversations/{cid}/agents",
                            json={"agent_ids": ["hermes", "cowork", "critic"]}, headers=h)
            assert r.status_code == 200

            pubsub = R.get_redis().pubsub()
            await pubsub.subscribe(R.conv_channel(cid))
            await asyncio.sleep(0.3)

            r = await c.post(f"{PREFIX}/conversations/{cid}/messages",
                             json={"text": "要不要做移动端 App？"}, headers=h)
            assert r.status_code == 200
            assert r.json()["agent_message"]["role"] == "roundtable"

            events = []
            loop = asyncio.get_event_loop()
            deadline = loop.time() + 30
            while loop.time() < deadline:
                m = await pubsub.get_message(ignore_subscribe_messages=True, timeout=6.0)
                if m:
                    events.append(json.loads(m["data"]))
                    if events[-1].get("type") == "done":
                        break
            await pubsub.unsubscribe()
            await pubsub.aclose()

            types = [e["type"] for e in events]
            assert "rt_start" in types
            rt_start = next(e for e in events if e["type"] == "rt_start")
            assert len(rt_start["agents"]) == 3
            streamed = {e["slot"] for e in events if e["type"] == "rt_token"}
            assert streamed == {0, 1, 2}
            assert "merge_start" in types and any(e["type"] == "merge_token" for e in events)
            assert events[-1]["type"] == "done" and events[-1]["status"] == "complete"

            # persisted roundtable message
            detail = (await c.get(f"{PREFIX}/conversations/{cid}", headers=h)).json()
            rt = [m for m in detail["messages"] if m["role"] == "roundtable"][-1]
            assert len(rt["content"]["replies"]) == 3
            assert all(rep["text"] for rep in rt["content"]["replies"])
            assert rt["content"]["merged"]["text"]
    finally:
        runner_task.cancel()
        try:
            await runner_task
        except asyncio.CancelledError:
            pass
        await runner.pool.close_all()
