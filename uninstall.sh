#!/usr/bin/env bash
# Native uninstall entry point for macOS / Linux. Locates Python and runs
# uninstall.py. Windows: use uninstall.ps1 (or run `python uninstall.py`).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON" ]; then
  echo "error: python3 (or python) not found on PATH." >&2
  exit 1
fi
exec "$PYTHON" "$REPO/uninstall.py" "$@"
