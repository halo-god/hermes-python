"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Test successful login with valid credentials."""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "test@hermes.io",
        "password": "Test@1234",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login fails with wrong password."""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "test@hermes.io",
        "password": "WrongPassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login fails with non-existent email."""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "nobody@hermes.io",
        "password": "Test@1234",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers, test_user):
    """Test /auth/me returns current user info."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name


@pytest.mark.asyncio
async def test_get_me_no_auth(client: AsyncClient):
    """Test /auth/me returns 401 without token."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    """Test /auth/me returns 401 with invalid token."""
    resp = await client.get("/api/v1/auth/me", headers={
        "Authorization": "Bearer invalid.token.here"
    })
    assert resp.status_code == 401
