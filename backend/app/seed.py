"""Idempotent seed: bootstrap the first super_admin account.

Run after migrations:  python -m app.seed
"""
from __future__ import annotations

import asyncio

from app.config import settings
from app.core.logging import configure_logging, logger
from app.db.base import async_session_maker
from app.schemas.user import UserCreate
from app.services import user_service


async def seed() -> None:
    configure_logging()
    async with async_session_maker() as db:
        existing = await user_service.get_by_email(db, settings.first_admin_email)
        if existing:
            logger.info("Seed: super_admin already exists (%s)", existing.email)
            return
        user = await user_service.create_user(
            db,
            UserCreate(
                email=settings.first_admin_email,
                name=settings.first_admin_name,
                handle="admin",
                password=settings.first_admin_password,
                role="super_admin",
                department="平台",
                title="超级管理员",
            ),
        )
        logger.info("Seed: created super_admin %s", user.email)


if __name__ == "__main__":
    asyncio.run(seed())
