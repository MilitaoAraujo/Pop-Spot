#!/bin/bash
# Instala dependências e liga o widget no login (Pop!_OS / Ubuntu / Debian).
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Updating package lists..."
sudo apt-get update -qq

echo "==> Installing system packages..."
sudo apt-get install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-gdkpixbuf-2.0 \
    gir1.2-gtklayershell-0.1 \
    libgtk-layer-shell0 \
    python3-dbus \
    python3-requests \
    python3-numpy \
    pulseaudio-utils \
    geoclue-2.0

sudo apt-get install -y fonts-inter || true

python3 -c "import requests" 2>/dev/null || pip3 install --user requests

echo ""
echo "==> Enabling autostart (systemd user)..."
bash "$SCRIPT_DIR/setup_autostart.sh"

echo ""
echo "Pop Spot is installed and will start on login."
echo "Uninstall:  bash $SCRIPT_DIR/uninstall.sh"
echo "Logs:       journalctl --user -u desktop-widget.service -f"
