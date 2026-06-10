"""RequestIDMiddleware (pure ASGI): contextvar propagation + header echo.

Proves the property BaseHTTPMiddleware couldn't guarantee — the correlation id
set by the middleware is visible to downstream app code (and thus its logging)
because they share one execution context.
"""
from __future__ import annotations

import pytest

from app.core.logging import request_id_var
from app.core.metrics import RequestIDMiddleware


def _http_scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    return {"type": "http", "headers": headers or []}


async def _noop_receive():
    return {"type": "http.request", "body": b"", "more_body": False}


@pytest.mark.asyncio
async def test_generated_id_visible_downstream_and_echoed():
    seen: dict[str, str] = {}
    sent: list[dict] = []

    async def downstream(scope, receive, send):
        # Same execution context as the middleware → the id must be visible here.
        seen["id"] = request_id_var.get()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def send(msg):
        sent.append(msg)

    await RequestIDMiddleware(downstream)(_http_scope(), _noop_receive, send)

    rid = seen["id"]
    assert rid and rid != "-"
    start = next(m for m in sent if m["type"] == "http.response.start")
    echoed = dict(start["headers"]).get(b"x-request-id", b"").decode()
    assert echoed == rid
    # Reset after the request completes — no leakage into the next context.
    assert request_id_var.get() == "-"


@pytest.mark.asyncio
async def test_incoming_id_is_propagated():
    seen: dict[str, str] = {}

    async def downstream(scope, receive, send):
        seen["id"] = request_id_var.get()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    sent: list[dict] = []

    async def send(msg):
        sent.append(msg)

    scope = _http_scope([(b"x-request-id", b"caller-trace-1")])
    await RequestIDMiddleware(downstream)(scope, _noop_receive, send)

    assert seen["id"] == "caller-trace-1"
    start = next(m for m in sent if m["type"] == "http.response.start")
    assert dict(start["headers"])[b"x-request-id"] == b"caller-trace-1"


@pytest.mark.asyncio
async def test_non_http_scope_passes_through():
    called = {"v": False}

    async def downstream(scope, receive, send):
        called["v"] = True

    await RequestIDMiddleware(downstream)({"type": "lifespan"}, _noop_receive, lambda m: None)
    assert called["v"]
