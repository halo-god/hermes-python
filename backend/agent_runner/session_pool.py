"""Per-conversation ACP subprocess pool.

One long-lived ACP session per conversation preserves the agent's context
across turns. Callbacks are rebound per prompt; prompts for a given
conversation are processed sequentially by the runner.
"""
from __future__ import annotations

import logging

from app.config import settings
from agent_runner.acp_client import ACPClient, OnFsWrite, OnUpdate

logger = logging.getLogger("hermes.pool")


class SessionPool:
    def __init__(self) -> None:
        self._clients: dict[str, ACPClient] = {}

    def _alive(self, c: ACPClient) -> bool:
        return (
            not c._closed
            and c._proc is not None
            and c._proc.returncode is None
        )

    async def get(
        self,
        conversation_id: str,
        command: list[str],
        cwd: str,
        on_update: OnUpdate,
        on_fs_write: OnFsWrite,
    ) -> tuple[ACPClient, str | None]:
        """Return (client, new_session_id_or_None). session id is set only when
        a fresh subprocess+session was created."""
        c = self._clients.get(conversation_id)
        if c is not None and self._alive(c):
            c.on_update = on_update
            c.on_fs_write = on_fs_write
            return c, None

        c = ACPClient(
            command,
            cwd,
            protocol_version=settings.acp_protocol_version,
            on_update=on_update,
            on_fs_write=on_fs_write,
        )
        await c.start()
        await c.initialize()
        if settings.hermes_acp_auth_method:
            await c.authenticate(settings.hermes_acp_auth_method)
        session_id = await c.new_session(cwd)
        self._clients[conversation_id] = c
        return c, session_id

    async def drop(self, conversation_id: str) -> None:
        c = self._clients.pop(conversation_id, None)
        if c:
            await c.stop()

    async def close_all(self) -> None:
        for c in list(self._clients.values()):
            await c.stop()
        self._clients.clear()
