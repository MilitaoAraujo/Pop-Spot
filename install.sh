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
    python3-pip \
    python3-venv \
    pulseaudio-utils \
    geoclue-2.0

sudo apt-get install -y fonts-inter || true

echo ""
echo "==> Python venv (PySide6; GTK do sistema via --system-site-packages)..."
if [[ ! -x "$SCRIPT_DIR/.venv/bin/python3" ]]; then
    python3 -m venv --system-site-packages "$SCRIPT_DIR/.venv"
fi
"$SCRIPT_DIR/.venv/bin/python3" -m pip install -q --upgrade pip
"$SCRIPT_DIR/.venv/bin/python3" -m pip install -q -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "==> Enabling autostart (systemd user)..."
bash "$SCRIPT_DIR/setup_autostart.sh"

echo ""
echo "Pop Spot is installed and will start on login."
echo "Uninstall:  bash $SCRIPT_DIR/uninstall.sh"
echo "Logs:       journalctl --user -u desktop-widget.service -f"
