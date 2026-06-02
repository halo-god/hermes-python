"""Team + project + task CRUD and the content-permission matrix (P3).

Asserts the governance matrix actually gates writes: owner all-access,
member can create projects but not delete, viewer can't create — and that
toggling the policy changes the outcome live.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import settings
from app.db.base import async_session_maker
from app.main import app
from app.schemas.user import UserCreate
from app.services import user_service

PREFIX = settings.api_v1_prefix


async def _services_ok() -> bool:
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _make_user(name: str) -> tuple[str, str]:
    email = f"{name}-{uuid.uuid4().hex[:8]}@hermes.io"
    pw = "Member@2026"
    async with async_session_maker() as db:
        await user_service.create_user(
            db, UserCreate(email=email, name=name, password=pw, role="member")
        )
    return email, pw


async def _login(c: AsyncClient, email: str, pw: str) -> dict:
    r = await c.post(f"{PREFIX}/auth/login", json={"method": "local", "username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_governance_matrix_gates_writes():
    if not await _services_ok():
        pytest.skip("PostgreSQL not reachable")

    member_email, member_pw = await _make_user("成员")
    viewer_email, viewer_pw = await _make_user("访客")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        owner_h = await _login(c, settings.first_admin_email, settings.first_admin_password)
        member_h = await _login(c, member_email, member_pw)
        viewer_h = await _login(c, viewer_email, viewer_pw)

        # owner creates a team → becomes owner
        r = await c.post(f"{PREFIX}/teams", json={"name": "设计组"}, headers=owner_h)
        assert r.status_code == 201, r.text
        team = r.json()
        tid = team["id"]
        assert team["my_role"] == "owner"

        # add member + viewer (owner has member.invite)
        r = await c.post(f"{PREFIX}/teams/{tid}/members", json={"email": member_email, "role": "member"}, headers=owner_h)
        assert r.status_code == 201, r.text
        r = await c.post(f"{PREFIX}/teams/{tid}/members", json={"email": viewer_email, "role": "viewer"}, headers=owner_h)
        assert r.status_code == 201, r.text
        member_uid = r.json()  # not used; viewer added

        # policy endpoint returns the matrix
        r = await c.get(f"{PREFIX}/teams/{tid}/policy", headers=owner_h)
        assert r.status_code == 200
        pol = r.json()
        assert pol["editable"] is True and pol["my_role"] == "owner"

        # member CAN create a project (default policy)
        r = await c.post(f"{PREFIX}/teams/{tid}/projects", json={"name": "品牌焕新"}, headers=member_h)
        assert r.status_code == 201, r.text
        pid = r.json()["id"]

        # viewer CANNOT create a project
        r = await c.post(f"{PREFIX}/teams/{tid}/projects", json={"name": "禁止"}, headers=viewer_h)
        assert r.status_code == 403, r.text

        # member CANNOT delete a project (project.delete = False by default)
        r = await c.delete(f"{PREFIX}/projects/{pid}", headers=member_h)
        assert r.status_code == 403, r.text

        # owner toggles policy: grant project.delete to member, then member can delete
        new_policy = dict(pol["policy"])
        new_policy["project.delete"] = {**new_policy["project.delete"], "member": True}
        r = await c.put(f"{PREFIX}/teams/{tid}/policy", json={"policy": new_policy}, headers=owner_h)
        assert r.status_code == 200, r.text

        # member now CAN delete (re-create one first to delete)
        r = await c.post(f"{PREFIX}/teams/{tid}/projects", json={"name": "可删项目"}, headers=member_h)
        pid2 = r.json()["id"]
        r = await c.delete(f"{PREFIX}/projects/{pid2}", headers=member_h)
        assert r.status_code == 204, r.text

        # tasks: member (project.edit=True) creates + updates + deletes
        r = await c.post(f"{PREFIX}/projects/{pid}/tasks", json={"title": "设计 logo"}, headers=member_h)
        assert r.status_code == 201, r.text
        task_id = r.json()["id"]
        assert r.json()["status"] == "todo"

        r = await c.patch(f"{PREFIX}/tasks/{task_id}", json={"status": "doing"}, headers=member_h)
        assert r.status_code == 200 and r.json()["status"] == "doing"

        r = await c.get(f"{PREFIX}/projects/{pid}/tasks", headers=viewer_h)
        assert r.status_code == 200 and len(r.json()) == 1  # viewer can read

        r = await c.delete(f"{PREFIX}/tasks/{task_id}", headers=viewer_h)
        assert r.status_code == 403  # viewer can't edit

        # viewer is a member, so they CAN list teams they belong to
        r = await c.get(f"{PREFIX}/teams", headers=viewer_h)
        assert any(t["id"] == tid for t in r.json())

        _ = member_uid
