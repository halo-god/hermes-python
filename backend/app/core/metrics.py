"""Prometheus metrics + an ASGI middleware that records request count/latency."""
from __future__ import annotations

import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
