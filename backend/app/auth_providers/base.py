"""Provider-neutral identity result + error type."""
from __future__ import annotations

from dataclasses import dataclass, field


class ProviderError(Exception):
    """Raised on provider auth failure (bad credentials, unreachable, …)."""


@dataclass
class IdentityInfo:
    external_id: str
    email: str
    name: str
    source: str
    department: str | None = None
    groups: list[str] = field(default_factory=list)
