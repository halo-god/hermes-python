"""Authentication flows: local login, token issuance, refresh, logout.

LDAP/AD and WeCom are stubbed with a clear NotImplemented path (P5).
"""
from __future__ import annotations

from datetime import datetime, timezone

import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import redis as redis_core
from app.core.security import (
    create_token,
    decode_token,
    needs_rehash,
    verify_password,
    hash_password,
)
from app.db.models.user import User
from app.schemas.auth import LoginRequest, TokenPair
from app.services import user_service


async def authenticate_local(db: AsyncSession, username: str, password: str) -> User:
    user = await user_service.get_by_email(db, username)
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误"
    )
    if not user or not user.password_hash:
        raise invalid
    if not verify_password(password, user.password_hash):
        raise invalid
    if not user.is_active or user.status == "inactive":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")

    # Transparent rehash on algorithm/param upgrade.
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.last_active_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return user


async def authenticate(db: AsyncSession, req: LoginRequest) -> User:
    if req.method == "local":
        if not req.username or not req.password:
            raise HTTPException(status_code=422, detail="请输入账号与密码")
        return await authenticate_local(db, str(req.username), req.password)

    # External identity providers (LDAP/AD now; WeCom/SAML/OIDC scaffolded).
    from app.services import identity_service

    if not req.username or not req.password:
        raise HTTPException(status_code=422, detail="请输入账号与密码")
    return await identity_service.authenticate_external(
        db, req.method, str(req.username), req.password
    )


def issue_tokens(user: User) -> TokenPair:
    access, _ = create_token(
        str(user.id), "access", extra={"role": user.role, "name": user.name}
    )
    refresh, _ = create_token(str(user.id), "refresh")
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> tuple[User, TokenPair]:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="刷新令牌无效")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="令牌类型错误")
    jti = payload.get("jti")
    if jti and await redis_core.is_blacklisted(jti):
        raise HTTPException(status_code=401, detail="令牌已失效")

    user = await user_service.get_by_id(db, _uuid(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已停用")

    # Rotate: blacklist the consumed refresh jti until its natural expiry.
    if jti:
        ttl = max(int(payload["exp"]) - int(datetime.now(tz=timezone.utc).timestamp()), 1)
        await redis_core.blacklist_jti(jti, ttl)

    return user, issue_tokens(user)


async def logout(refresh_token: str | None) -> None:
    if not refresh_token:
        return
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        return
    jti = payload.get("jti")
    if jti:
        ttl = max(int(payload["exp"]) - int(datetime.now(tz=timezone.utc).timestamp()), 1)
        await redis_core.blacklist_jti(jti, ttl)


def _uuid(value: str):
    import uuid

    return uuid.UUID(value)
