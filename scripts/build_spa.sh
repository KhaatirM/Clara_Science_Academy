#!/usr/bin/env bash
# Build the React SPA into static/spa/ (gitignored). Used by Render and local CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

NODE_VERSION="${NODE_VERSION:-20.18.1}"
NODE_DIR="${ROOT}/.render-node"
NODE_DIST="node-v${NODE_VERSION}-linux-x64"

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node/npm not on PATH; installing ${NODE_DIST}..."
  mkdir -p "$NODE_DIR"
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/${NODE_DIST}.tar.xz" \
    | tar -xJ -C "$NODE_DIR"
  export PATH="${NODE_DIR}/${NODE_DIST}/bin:${PATH}"
fi

echo "Using node $(node -v) / npm $(npm -v)"
cd frontend
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
npm run build
cd "$ROOT"

test -f static/spa/index.html
echo "SPA build OK: static/spa/index.html"
