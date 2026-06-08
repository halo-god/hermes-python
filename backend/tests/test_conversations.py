"""Tests for conversation and group chat endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_personal_conversation(client: AsyncClient, auth_headers):
    """Test creating a personal conversation."""
    resp = await client.post("/api/v1/conversations", json={
        "title": "Test Chat",
        "primary_agent_id": "hermes",
    }, headers=auth_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["title"] == "Test Chat"
    assert data["type"] == "personal"


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, auth_headers):
    """Test listing conversations returns user's conversations."""
    # Create one first
    await client.post("/api/v1/conversations", json={
        "title": "My Chat",
        "primary_agent_id": "hermes",
    }, headers=auth_headers)

    resp = await client.get("/api/v1/conversations", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_create_conversation_no_auth(client: AsyncClient):
    """Test creating conversation without auth fails."""
    resp = await client.post("/api/v1/conversations", json={
        "title": "No Auth Chat",
        "primary_agent_id": "hermes",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_group_requires_team(client: AsyncClient, auth_headers):
    """Test creating group chat requires team_id."""
    resp = await client.post("/api/v1/conversations/group", json={
        "title": "Test Group",
        "member_agent_ids": ["hermes"],
    }, headers=auth_headers)
    # Should fail without team_id (422 validation error)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint is accessible."""
    resp = await client.get("/api/v1/healthz")
    assert resp.status_code == 200
