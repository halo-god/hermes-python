"""End-to-end conversation streaming test (P2).

Runs the Agent Runner in-process (background task), drives the API via
httpx ASGITransport, and collects streamed events off the Redis channel —
proving: send → Redis Stream → ACP subprocess (mock) → Redis Pub/Sub →
tokens + tool + produced file → persisted message + workspace file.

Requires reachable PostgreSQL + Redis and a seeded admin.
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
async def test_conversation_stream_e2e():
    if not await _services_ok():
        pytest.skip("PostgreSQL/Redis not reachable — start services + migrate + seed")

    runner = Runner()
    runner_task = asyncio.create_task(runner.run())
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            # login
            r = await c.post(
                f"{PREFIX}/auth/login",
                json={
                    "method": "local",
                    "username": settings.first_admin_email,
                    "password": settings.first_admin_password,
                },
            )
            assert r.status_code == 200, r.text
            h = {"Authorization": f"Bearer {r.json()['access_token']}"}

            # create conversation
            r = await c.post(
                f"{PREFIX}/conversations", json={"primary_agent_id": "hermes"}, headers=h
            )
            assert r.status_code == 201, r.text
            cid = r.json()["id"]

            # subscribe to the live channel before sending
            pubsub = R.get_redis().pubsub()
            await pubsub.subscribe(R.conv_channel(cid))
            await asyncio.sleep(0.3)

            # send
            r = await c.post(
                f"{PREFIX}/conversations/{cid}/messages",
                json={"text": "帮我写一个项目启动会的会议纪要"},
                headers=h,
            )
            assert r.status_code == 200, r.text

            # collect events
            events = []
            loop = asyncio.get_event_loop()
            deadline = loop.time() + 25
            while loop.time() < deadline:
                m = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                if m:
                    ev = json.loads(m["data"])
                    events.append(ev)
                    if ev.get("type") == "done":
                        break
            await pubsub.unsubscribe()
            await pubsub.aclose()

            types = [e["type"] for e in events]
            assert "token" in types, types
            assert "file" in types, types
            assert any(e["type"] == "done" and e.get("status") == "complete" for e in events)

            # persisted agent message
            r = await c.get(f"{PREFIX}/conversations/{cid}", headers=h)
            agent_msgs = [m for m in r.json()["messages"] if m["role"] == "agent"]
            assert agent_msgs[-1]["status"] == "complete"
            assert agent_msgs[-1]["content"]["text"]

            # persisted workspace file
            r = await c.get(f"{PREFIX}/conversations/{cid}/files", headers=h)
            files = r.json()
            assert files and files[0]["name"]
    finally:
        runner_task.cancel()
        try:
            await runner_task
        except asyncio.CancelledError:
            pass
        await runner.pool.close_all()
