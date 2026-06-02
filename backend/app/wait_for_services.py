"""Block until PostgreSQL and Redis are reachable (used by the container entrypoint)."""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.core.redis import get_redis


async def _wait_pg(timeout: int = 60) -> None:
    engine = create_async_engine(settings.database_url)
    for attempt in range(timeout):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print("  postgres: ready")
            await engine.dispose()
            return
        except Exception:
            await asyncio.sleep(1)
    await engine.dispose()
    print("  postgres: NOT ready", file=sys.stderr)
    raise SystemExit(1)


async def _wait_redis(timeout: int = 60) -> None:
    for attempt in range(timeout):
        try:
            await get_redis().ping()
            print("  redis: ready")
            return
        except Exception:
            await asyncio.sleep(1)
    print("  redis: NOT ready", file=sys.stderr)
    raise SystemExit(1)


async def main() -> None:
    await _wait_pg()
    await _wait_redis()


if __name__ == "__main__":
    asyncio.run(main())
