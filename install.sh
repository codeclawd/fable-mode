#!/usr/bin/env bash
# Native entry point for macOS / Linux. Locates Python and runs the real,
# cross-platform installer (install.py). Windows: use install.ps1 (or run
# `python install.py` directly on any OS).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON" ]; then
  echo "error: python3 (or python) not found on PATH — required for the hooks." >&2
  exit 1
fi
exec "$PYTHON" "$REPO/install.py" "$@"
