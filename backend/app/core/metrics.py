"""Prometheus metrics + ASGI middleware (request count/latency + correlation id)."""
from __future__ import annotations

import time
import uuid

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

HTTP_REQUESTS = Counter(
    "hermes_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "hermes_http_request_seconds", "HTTP request latency", ["method", "path"]
)
LOGINS = Counter("hermes_logins_total", "Login attempts", ["result"])
MESSAGES = Counter("hermes_messages_total", "Messages dispatched")


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path) if route else "other"


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        path = _route_path(request)
        elapsed = time.perf_counter() - start
        HTTP_LATENCY.labels(request.method, path).observe(elapsed)
        HTTP_REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        return response


class RequestIDMiddleware:
    """Assign/propagate a correlation id, bind it for logging, echo it back.

    Pure ASGI (not BaseHTTPMiddleware): BaseHTTPMiddleware buffers responses
    through an anyio memory stream — bad for long-lived SSE — and runs in a
    separate task, so a contextvar set there wouldn't reliably reach the route
    handler's logging. Setting it here, before awaiting the inner app in the
    same context, threads the id through every downstream log line.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope.get("headers") or {})
        raw = incoming.get(b"x-request-id", b"").decode() or uuid.uuid4().hex[:12]
        rid_bytes = raw.encode()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers.append((b"x-request-id", rid_bytes))
                message["headers"] = headers
            await send(message)

        token = request_id_var.set(raw)
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_var.reset(token)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
