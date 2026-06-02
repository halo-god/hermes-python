"""Structured-ish logging setup."""
from __future__ import annotations

import logging
import sys

from app.config import settings


def configure_logging() -> None:
    level = logging.DEBUG if settings.debug else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers on uvicorn reload.
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)

    # Tame noisy libraries.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("hermes")
