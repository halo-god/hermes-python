"""Password hashing (argon2id) and JWT issuance/verification."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from app.config import settings

_ph = PasswordHasher()

TokenType = Literal["access", "refresh"]


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_token(
    subject: str,
    token_type: TokenType,
    extra: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Returns (encoded_jwt, jti)."""
    jti = uuid.uuid4().hex
    if token_type == "access":
        expire = _now() + timedelta(minutes=settings.access_token_ttl_minutes)
    else:
        expire = _now() + timedelta(days=settings.refresh_token_ttl_days)

    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": int(_now().timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra:
        payload.update(extra)

    encoded = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return encoded, jti


def decode_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
