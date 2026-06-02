"""Real-CLI integration path: a faithful `hermes` binary on PATH.

We can't ship NousResearch's real CLI here (needs network + model creds), so we
put an executable literally named `hermes` on PATH that answers `hermes
--version` and runs a real ACP stdio server for `hermes acp`. This exercises the
exact production path: PATH discovery → register as kind=acp_cli (NOT the mock
fallback) → spawn `hermes acp` → speak ACP → stream + produce a file.

The only thing this can't cover is NousResearch's actual model output, which is
inherently external.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

from agent_runner import discovery
from agent_runner.acp_client import ACPClient

MOCK = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "agent_runner", "mock_agent.py")
)


def _write_fake_hermes(dirpath: str) -> str:
    path = os.path.join(dirpath, "hermes")
    with open(path, "w") as f:
        f.write("#!/bin/sh\n")
        f.write('case "$1" in\n')
        f.write('  --version) echo "hermes 0.15.0 (fake-acp)" ;;\n')
        f.write(f'  acp) exec "{sys.executable}" "{MOCK}" --persona hermes ;;\n')
        f.write("  *) : ;;\n")
        f.write("esac\n")
    os.chmod(path, 0o755)
    return path


@pytest.mark.asyncio
async def test_discovers_and_runs_real_hermes_acp():
    tmp = tempfile.mkdtemp()
    fake = _write_fake_hermes(tmp)
    old_path = os.environ["PATH"]
    os.environ["PATH"] = tmp + os.pathsep + old_path
    try:
        agents = await discovery.scan()

        # discovered as a REAL ACP CLI, not the bundled mock fallback
        hermes = next((a for a in agents if a.id == "hermes"), None)
        assert hermes is not None
        assert hermes.kind == "acp_cli"
        assert hermes.command == [fake, "acp"]
        assert hermes.version and "fake-acp" in hermes.version
        # mock-only personas are NOT registered when a real hermes is present
        assert not any(a.id in ("cowork", "critic") for a in agents)

        # full ACP turn through `hermes acp`
        got = {"text": ""}
        files: list[str] = []

        async def on_update(u):
            if u.get("sessionUpdate") == "agent_message_chunk":
                got["text"] += u["content"]["text"]

        async def on_fs(path, content):
            files.append(path)

        c = ACPClient(hermes.command, cwd="/tmp", on_update=on_update, on_fs_write=on_fs)
        await c.start()
        init = await c.initialize()
        assert init.get("protocolVersion") == 1
        sid = await c.new_session("/tmp")
        stop = await c.prompt("真机联调：写个启动会纪要")
        await c.stop()

        assert sid and stop == "end_turn"
        assert got["text"].strip()
        assert any("会议纪要" in f for f in files)
    finally:
        os.environ["PATH"] = old_path
