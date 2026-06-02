"""Admin console + rate limiting + history (P4).

Covers: admin-gated user CRUD, audit-log recording (login + admin actions),
system settings update propagating the live rate limit, per-minute send
throttling (429), and conversation search + bulk delete.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import settings
from app.core import ratelimit
from app.core.redis import get_redis
from app.db.base import async_session_maker
from app.main import app
from app.schemas.user import UserCreate
from app.services import user_service

PREFIX = settings.api_v1_prefix


async def _ok() -> bool:
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
        await get_redis().ping()
        return True
    except Exception:
        return False


async def _login(c, email, pw):
    r = await c.post(f"{PREFIX}/auth/login", json={"method": "local", "username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_admin_console_and_limits():
    if not await _ok():
        pytest.skip("PostgreSQL/Redis not reachable")

    # a non-admin member
    member_email = f"m-{uuid.uuid4().hex[:8]}@hermes.io"
    async with async_session_maker() as db:
        await user_service.create_user(
            db, UserCreate(email=member_email, name="路人", password="Member@2026", role="member")
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        admin_h = await _login(c, settings.first_admin_email, settings.first_admin_password)
        member_h = await _login(c, member_email, "Member@2026")

        # non-admin blocked from admin routes
        assert (await c.get(f"{PREFIX}/admin/stats", headers=member_h)).status_code == 403

        # stats (incl. distributions)
        r = await c.get(f"{PREFIX}/admin/stats", headers=admin_h)
        assert r.status_code == 200 and r.json()["users"] >= 2
        assert "role_distribution" in r.json() and "source_distribution" in r.json()

        # roles & permission matrix
        assert (await c.get(f"{PREFIX}/admin/roles", headers=member_h)).status_code == 403
        r = await c.get(f"{PREFIX}/admin/roles", headers=admin_h)
        assert r.status_code == 200
        body = r.json()
        assert {x["id"] for x in body["roles"]} == {"super_admin", "admin", "team_admin", "member", "viewer"}
        assert sum(x["users"] for x in body["roles"]) >= 2  # live counts
        perm_ids = {it["id"] for g in body["permissions"] for it in g["items"]}
        assert {"chat.create", "admin.roles"} <= perm_ids

        # admin creates a user
        new_email = f"u-{uuid.uuid4().hex[:8]}@hermes.io"
        r = await c.post(f"{PREFIX}/admin/users",
                         json={"email": new_email, "name": "新人", "password": "Newbie@2026", "role": "member"},
                         headers=admin_h)
        assert r.status_code == 201, r.text
        new_id = r.json()["id"]

        # admin promotes them
        r = await c.patch(f"{PREFIX}/admin/users/{new_id}", json={"role": "team_admin"}, headers=admin_h)
        assert r.status_code == 200 and r.json()["role"] == "team_admin"

        # user search
        r = await c.get(f"{PREFIX}/admin/users", params={"q": "新人"}, headers=admin_h)
        assert any(u["id"] == new_id for u in r.json())

        # audit captured login + admin actions
        r = await c.get(f"{PREFIX}/admin/audit", headers=admin_h)
        actions = {e["action"] for e in r.json()}
        assert "auth.login" in actions
        assert "admin.user.create" in actions and "admin.user.update" in actions

        # failed login is audited as fail
        bad = await c.post(f"{PREFIX}/auth/login",
                           json={"method": "local", "username": settings.first_admin_email, "password": "wrong"})
        assert bad.status_code == 401
        r = await c.get(f"{PREFIX}/admin/audit", params={"result": "fail"}, headers=admin_h)
        assert any(e["action"] == "auth.login" for e in r.json())

        # system settings: lower the rate limit live
        s = (await c.get(f"{PREFIX}/admin/settings", headers=admin_h)).json()
        s["data"]["model_gateway"]["rate_limit_per_min"] = 2
        r = await c.put(f"{PREFIX}/admin/settings", json={"data": s["data"]}, headers=admin_h)
        assert r.status_code == 200
        assert await ratelimit.get_rate_limit() == 2

        # rate limit enforced on send (limit just set to 2)
        await get_redis().delete(f"rl:msg:{member_h}")  # noop key; ensure clean below
        r = await c.post(f"{PREFIX}/conversations", json={"primary_agent_id": "hermes"}, headers=member_h)
        cid = r.json()["id"]
        # clear this member's window, then send 2 OK + 1 throttled
        # (resolve member id from token via /auth/me)
        me = (await c.get(f"{PREFIX}/auth/me", headers=member_h)).json()
        await get_redis().delete(f"rl:msg:{me['id']}")
        codes = []
        for _ in range(3):
            rr = await c.post(f"{PREFIX}/conversations/{cid}/messages", json={"text": "hi"}, headers=member_h)
            codes.append(rr.status_code)
        assert codes.count(200) == 2 and codes.count(429) == 1, codes

        # restore a sane limit for other tests
        s["data"]["model_gateway"]["rate_limit_per_min"] = 1000
        await c.put(f"{PREFIX}/admin/settings", json={"data": s["data"]}, headers=admin_h)

        # history: search + bulk delete
        await c.post(f"{PREFIX}/conversations", json={"title": "唯一关键词XZ", "primary_agent_id": "hermes"}, headers=member_h)
        r = await c.get(f"{PREFIX}/conversations", params={"q": "关键词XZ"}, headers=member_h)
        assert len(r.json()) == 1
        ids = [conv["id"] for conv in (await c.get(f"{PREFIX}/conversations", headers=member_h)).json()]
        r = await c.post(f"{PREFIX}/conversations/bulk-delete", json={"ids": ids}, headers=member_h)
        assert r.json()["deleted"] == len(ids)
        assert (await c.get(f"{PREFIX}/conversations", headers=member_h)).json() == []
