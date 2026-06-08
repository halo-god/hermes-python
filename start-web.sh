#!/bin/bash
# Start the Hermes Python frontend (vite preview, port 5173 by default).
# Run from anywhere — script self-locates via BASH_SOURCE.
#
# Requires Node.js >= 20 (vite 5+ uses top-level await).
# Override the node binary with NODE_BIN env var if your system node is older:
#   NODE_BIN=/path/to/nodejs/bin/node ./start-web.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"
NODE_BIN="${NODE_BIN:-node}"

cd "${FRONTEND_DIR}"

if [[ ! -d "${FRONTEND_DIR}/node_modules/vite" ]]; then
  echo "ERROR: vite not installed. Run: cd ${FRONTEND_DIR} && npm install" >&2
  exit 1
fi

if [[ ! -d "${FRONTEND_DIR}/dist" ]]; then
  echo "ERROR: dist not built. Run: cd ${FRONTEND_DIR} && npm run build" >&2
  exit 1
fi

NODE_VERSION="$("${NODE_BIN}" --version 2>/dev/null || echo "unknown")"
NODE_MAJOR="$(echo "${NODE_VERSION}" | sed -E 's/^v([0-9]+).*/\1/')"
if [[ "${NODE_MAJOR}" =~ ^[0-9]+$ ]] && [[ "${NODE_MAJOR}" -lt 20 ]]; then
  echo "ERROR: Node ${NODE_VERSION} too old (need >= 20). Set NODE_BIN to a newer node." >&2
  exit 1
fi

export NODE_ENV="${NODE_ENV:-production}"
PORT="${HERMES_WEB_PORT:-5173}"
HOST="${HERMES_WEB_HOST:-0.0.0.0}"

exec "${NODE_BIN}" "${FRONTEND_DIR}/node_modules/vite/bin/vite.js" preview \
  --port "${PORT}" \
  --host "${HOST}"
