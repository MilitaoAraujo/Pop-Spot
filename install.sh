#!/bin/bash
# Install dependencies for the Desktop Widget
set -e

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
    fonts-inter 2>/dev/null || true

# python3-requests via pip if apt version is too old
python3 -c "import requests" 2>/dev/null || pip3 install --user requests

echo ""
echo "==> All dependencies installed!"
echo ""
echo "Run the widget with:"
echo "    python3 $(dirname "$0")/widget.py &"
echo ""
echo "Or run the autostart setup:"
echo "    bash $(dirname "$0")/setup_autostart.sh"
