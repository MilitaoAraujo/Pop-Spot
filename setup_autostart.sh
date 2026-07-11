#!/usr/bin/env bash
# Liga o widget ao abrir sessão (Pop!_OS COSMIC, GNOME, etc.) via systemd user.
# Evita só o ~/.config/autostart, que no COSMIC sobe antes do Wayland estar pronto.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$SCRIPT_DIR/launch_desktop_widget.sh"
SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SERVICE_FILE="$SYSTEMD_USER_DIR/desktop-widget.service"
AUTOSTART_DIR="$HOME/.config/autostart"
LEGACY_DESKTOP="$AUTOSTART_DIR/desktop-widget.desktop"

chmod +x "$LAUNCHER"

mkdir -p "$SYSTEMD_USER_DIR"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Desktop Widget (GTK — clock · weather · Spotify)
PartOf=graphical-session.target
# Espera sessão gráfica subir primeiro (COSMIC/GNOME trazem este alvo no login).
After=graphical-session.target

[Service]
Type=simple
# Evita dois processos ao relogar: só um serviço.
ExecStart=${LAUNCHER}
Restart=always
RestartSec=4
StartLimitBurst=5
StartLimitIntervalSec=120

[Install]
# Dispara quando você faz login (usuário systemd ativo).
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable desktop-widget.service
systemctl --user restart desktop-widget.service 2>/dev/null || \
  systemctl --user start desktop-widget.service

if [[ -f "$LEGACY_DESKTOP" ]]; then
  echo ""
  echo "Removendo $LEGACY_DESKTOP (evita abrir duas vezes: XDG autostart + systemd)."
  rm -f "$LEGACY_DESKTOP"
fi

echo ""
echo "Serviço instalado:"
echo "  $SERVICE_FILE"
echo "Status: $(systemctl --user is-enabled desktop-widget.service 2>/dev/null || echo '?')"
systemctl --user --no-pager status desktop-widget.service 2>/dev/null | head -15 || true
echo ""
echo "No próximo boot / login ele sobe sozinho (sem terminal)."
echo "Ver log: journalctl --user -u desktop-widget.service -f"
echo "Parar automático: systemctl --user disable --now desktop-widget.service"
