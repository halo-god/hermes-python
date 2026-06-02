"""Agent + Profile DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    kind: str
    available: bool
    official: bool
    version: str | None
    color: str | None
    icon: str | None
    description: str | None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    handle: str
    scope: str  # personal | team | global
    color: str
    icon: str
    desc: str
    default_agent_id: str
    default_model: str
    team_id: uuid.UUID | None = None
    is_active: bool = True
    path: str | None = None


class ProfileCreate(BaseModel):
    name: str
    handle: str
    scope: str = "personal"
    color: str = "#b8852a"
    icon: str = "brand"
    desc: str = ""
    default_agent_id: str = "hermes"
    default_model: str = "hermes-4"
    team_id: uuid.UUID | None = None


class ProfileUpdate(BaseModel):
    name: str | None = None
    handle: str | None = None
    scope: str | None = None
    color: str | None = None
    icon: str | None = None
    desc: str | None = None
    default_agent_id: str | None = None
    default_model: str | None = None
    team_id: uuid.UUID | None = None
    is_active: bool | None = None
    path: str | None = None


class ScanProfilesResponse(BaseModel):
    created: int
    message: str
    version: str
    profiles_found: int
    hermes_path: str | None = None   # absolute path where hermes binary was found
    hermes_home: str | None = None   # hermes home directory that was scanned
    errors: list[str] = []           # non-fatal warnings / errors encountered
