#!/usr/bin/env bash
# Atalho: mesma UI oficial (Qt). Preferível: bash launch_desktop_widget.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PY="$SCRIPT_DIR/.venv/bin/python3"
if [[ ! -x "$PY" ]]; then PY=python3; fi
unset QT_QPA_PLATFORM || true
exec "$PY" "$SCRIPT_DIR/main.py"
