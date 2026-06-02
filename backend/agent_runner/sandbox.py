"""Sandboxing for agent subprocesses.

Two layers:
  1. POSIX rlimits (CPU/NPROC/FSIZE, optional address space) applied in a
     preexec hook — cheap, always-on when enabled.
  2. An optional wrapper command (bubblewrap/firejail/gVisor `runsc`) prefixed
     to the argv for filesystem/network isolation — set SANDBOX_CMD to enable.

Strong memory isolation + network egress control are best handled by the
deployment (cgroups v2 / gVisor RuntimeClass / network policy); see
docs/方案设计.md §12. RLIMIT_AS is opt-in (SANDBOX_MEMORY_MB>0) because a low
value can make exec() fail after fork on a large parent.
"""
from __future__ import annotations

import logging
import shlex
from typing import Callable

from app.config import settings

logger = logging.getLogger("hermes.sandbox")


def build_argv(command: list[str], cwd: str = "") -> list[str]:
    """Prefix the optional wrapper command; `{cwd}` in the wrapper is templated
    to the agent's working dir (e.g. for bind-mounting the workspace)."""
    if settings.sandbox_cmd.strip():
        wrapper = [tok.replace("{cwd}", cwd) for tok in shlex.split(settings.sandbox_cmd)]
        return wrapper + command
    return command


def preexec_fn() -> Callable[[], None] | None:
    """Return a child preexec callable applying rlimits, or None if unavailable."""
    if not settings.sandbox_enabled:
        return None
    try:
        import resource  # POSIX only
    except ImportError:
        return None

    cpu = settings.sandbox_cpu_seconds
    nproc = settings.sandbox_nproc
    fsize = settings.sandbox_fsize_mb * 1024 * 1024
    mem = settings.sandbox_memory_mb * 1024 * 1024  # 0 = disabled

    def _apply() -> None:
        def _set(res, soft):
            try:
                resource.setrlimit(res, (soft, soft))
            except (ValueError, OSError):
                pass

        if cpu > 0:
            _set(resource.RLIMIT_CPU, cpu)
        if nproc > 0 and hasattr(resource, "RLIMIT_NPROC"):
            _set(resource.RLIMIT_NPROC, nproc)
        if fsize > 0:
            _set(resource.RLIMIT_FSIZE, fsize)
        if mem > 0:
            _set(resource.RLIMIT_AS, mem)

    return _apply
