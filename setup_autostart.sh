#!/bin/bash
# Configure the widget to start automatically on login (GNOME / Pop!_OS)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/desktop-widget.desktop"

mkdir -p "$AUTOSTART_DIR"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Desktop Widget
Comment=Clock · Weather · Spotify Now Playing
Exec=python3 $SCRIPT_DIR/main.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
EOF

echo "Autostart entry created at:"
echo "  $DESKTOP_FILE"
echo ""
echo "The widget will launch automatically on your next login."
echo ""
echo "To start it right now:"
echo "  python3 $SCRIPT_DIR/main.py &"
