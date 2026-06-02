"""Auth endpoints: login / refresh / logout / me / providers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models.user import User
from app.deps import get_current_user
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    ProviderInfo,
    RefreshRequest,
    TokenPair,
)
from app.core import metrics
from app.schemas.user import UserOut
from app.services import audit_service, auth_service

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    ip = request.client.host if request.client else None
    who = str(req.username or "")
    try:
        user = await auth_service.authenticate(db, req)
    except HTTPException as exc:
        metrics.LOGINS.labels("fail").inc()
        await audit_service.record(
            action="auth.login", actor_name=who, target=who, ip=ip,
            result="fail", meta={"reason": exc.detail}, db=db,
        )
        await db.commit()
        raise
    metrics.LOGINS.labels("ok").inc()
    tokens = auth_service.issue_tokens(user)
    await audit_service.record(
        action="auth.login", actor_id=user.id, actor_name=user.name,
        ip=ip, result="ok", db=db,
    )
    await db.commit()
    return LoginResponse(**tokens.model_dump(), user=UserOut.model_validate(user))


@router.post("/refresh", response_model=TokenPair)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    _, tokens = await auth_service.refresh_tokens(db, req.refresh_token)
    return tokens


@router.post("/logout", status_code=204)
async def logout(req: RefreshRequest | None = None) -> Response:
    await auth_service.logout(req.refresh_token if req else None)
    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/change-password", status_code=204)
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    from app.core.security import verify_password, hash_password

    if not user.password_hash or not verify_password(req.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    user.password_hash = hash_password(req.new_password)
    await db.commit()
    return Response(status_code=204)


@router.get("/providers", response_model=list[ProviderInfo])
async def providers(db: AsyncSession = Depends(get_db)) -> list[ProviderInfo]:
    """Drives the login page tabs; reflects which providers admins enabled."""
    from app.services import identity_service

    rows = await identity_service.list_providers(db)
    out = [ProviderInfo(id="local", label="账号密码", enabled=True, kind="local")]
    out += [
        ProviderInfo(id=p.id, label=p.label, enabled=p.enabled, kind=p.id) for p in rows
    ]
    return out
