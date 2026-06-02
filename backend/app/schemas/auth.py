"""Auth DTOs."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserOut


class LoginRequest(BaseModel):
    method: Literal["local", "ldap", "wecom"] = "local"
    # local / ldap
    username: EmailStr | str | None = None
    password: str | None = None
    remember_device: bool = False
    # wecom (reserved): a scan ticket would go here


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access token TTL seconds


class LoginResponse(TokenPair):
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class ProviderInfo(BaseModel):
    id: str
    label: str
    enabled: bool
    kind: str  # local | ldap | wecom | saml | oidc | feishu
