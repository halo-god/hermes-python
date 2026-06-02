"""Hermes Agent Runner — ACP gateway.

Scans the host for installed agent CLIs, spawns them as sandboxed ACP
subprocesses (JSON-RPC over stdio), and bridges their streaming output to the
web tier via Redis (Stream in, Pub/Sub out).
"""
