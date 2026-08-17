#!/usr/bin/env bash
# Remove o autostart do Pop Spot (não apaga a pasta do projeto).
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SERVICE_FILE="$SYSTEMD_USER_DIR/desktop-widget.service"
LEGACY_DESKTOP="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/desktop-widget.desktop"

if systemctl --user list-unit-files desktop-widget.service >/dev/null 2>&1; then
  systemctl --user disable --now desktop-widget.service 2>/dev/null || true
fi

rm -f "$SERVICE_FILE" "$LEGACY_DESKTOP"
systemctl --user daemon-reload 2>/dev/null || true

pkill -f "${SCRIPT_DIR}/main.py" 2>/dev/null || true

echo "Pop Spot autostart removed."
echo "The project folder was not deleted."
echo "To start again: bash ${SCRIPT_DIR}/setup_autostart.sh"
