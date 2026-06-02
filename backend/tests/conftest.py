"""Test fixtures.

pytest-asyncio gives each test its own event loop, but our module-global
async engine + Redis client bind their connection pools to the loop that first
used them. Reset both around every test so each runs against a pool bound to
its own loop (avoids cross-loop 'attached to a different loop' errors).
"""
from __future__ import annotations

import pytest

from app.core import redis as redis_core
from app.db.base import engine


@pytest.fixture(autouse=True)
async def _reset_global_clients():
    await engine.dispose()
    await redis_core.close_redis()
    yield
    await engine.dispose()
    await redis_core.close_redis()
