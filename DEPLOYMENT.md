# Bare-metal Deployment Scripts

The three `start-*.sh` scripts in this directory run the API, agent runner, and
frontend preview server without Docker. Use them when you want long-lived
systemd-managed services on a Linux host instead of the `make up` Docker stack.

## Scripts

| Script | Service | Default port |
|--------|---------|--------------|
| `start-api.sh` | FastAPI backend (uvicorn) | `8001` |
| `start-agent.sh` | Agent runner (ACP consumer) | n/a |
| `start-web.sh` | Frontend (vite preview) | `5173` |

All three are self-locating — `cd` anywhere and run them with the absolute path,
or symlink them into systemd unit files.

## Prerequisites

- Python 3.11+ with a venv at `backend/.venv` (`python -m venv .venv && pip install -e ".[dev]"`)
- Node.js **>= 20** for the frontend (vite 5+ uses top-level await)
- Postgres, Redis, MinIO running locally (see `docker-compose.yml` or run them
  manually)
- `frontend/dist/` already built (`npm install && npm run build`)
- `alembic upgrade head` run at least once

## Environment Variables

### `start-api.sh`

| Var | Default | Purpose |
|-----|---------|---------|
| `HERMES_HOME` | `$HOME/.hermes` | Hermes Agent home dir |
| `HERMES_API_PORT` | `8001` | uvicorn port |
| `HERMES_API_HOST` | `0.0.0.0` | uvicorn host |
| `HERMES_API_LOG_LEVEL` | `info` | uvicorn log level |
| `HERMES_AUTO_MIGRATE` | `0` | If `1`, run `alembic upgrade head` before starting |
| `VENV_DIR` | `backend/.venv` | Override the venv location |

### `start-agent.sh`

All vars are overridable; defaults match `docker-compose.yml`:

| Var | Default |
|-----|---------|
| `DATABASE_URL` | `postgresql+asyncpg://hermes:hermes@localhost:5432/hermes` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `SECRET_KEY` | placeholder — **must change in production** |
| `WORKSPACE_ROOT` | `$HOME/hermes-workspaces` |
| `HERMES_HOME` | `$HOME/.hermes` |
| `HERMES_BIN` | `hermes` |
| `HERMES_ACP_ARGS` | `["acp"]` |
| `ACP_ALLOW_MOCK_FALLBACK` | `true` |
| `ACP_CONSUMER` | `runner-1` |
| `STORAGE_BACKEND` | `minio` |
| `MINIO_ENDPOINT` | `http://localhost:9000` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` / `MINIO_BUCKET` | `hermes` / `hermes-minio-secret` / `hermes-workspace` |
| `SANDBOX_ENABLED` | `false` |

### `start-web.sh`

| Var | Default | Purpose |
|-----|---------|---------|
| `NODE_BIN` | `node` (PATH lookup) | Path to a Node.js >= 20 binary |
| `HERMES_WEB_PORT` | `5173` | vite preview port |
| `HERMES_WEB_HOST` | `0.0.0.0` | vite preview host |
| `NODE_ENV` | `production` | Node env |

If your system `node` is older than 20, set `NODE_BIN` to a newer binary:

```bash
NODE_BIN=/opt/node-v22/bin/node ./start-web.sh
```

## systemd User Service Example

Drop this into `~/.config/systemd/user/hermes-python-api.service`:

```ini
[Unit]
Description=Hermes Python API
After=network-online.target

[Service]
Type=simple
ExecStart=/path/to/hermes-python/start-api.sh
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

Then:

```bash
loginctl enable-linger $USER   # so the service runs without an active login
systemctl --user daemon-reload
systemctl --user enable --now hermes-python-api.service
```

Repeat for `hermes-python-agent.service` and `hermes-python-web.service`.

## Dev Proxy

The vite dev proxy target is configurable via `VITE_API_PROXY_TARGET` (set in
`frontend/.env.local`). Default is `http://localhost:8000` (the Docker port).
If you run the API on `8001` bare-metal, drop this into `frontend/.env.local`:

```
VITE_API_PROXY_TARGET=http://localhost:8001
```

Then rebuild the frontend.

## Troubleshooting

- **`ImportError: cannot import name 'PasswordHasher' from 'argon2'`** — uvicorn
  is being picked from the system Python (which has the unrelated `argon2`
  package), not the venv. Make sure `VENV_DIR` points at a venv where
  `argon2-cffi` is installed. The script enforces this by calling
  `${VENV_DIR}/bin/uvicorn` directly.
- **`SyntaxError: Unexpected reserved word` from vite** — your `node` is too old
  (< 20). Set `NODE_BIN` to a newer binary.
- **`vite: command not found`** — `npm install` hasn't been run in `frontend/`.
