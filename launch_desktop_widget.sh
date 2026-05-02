#!/usr/bin/env bash
# Iniciação pelo ~/.config/autostart — repõe variáveis que o COSMIC nem sempre exporta ao .desktop na hora certa (Wayland, D-Bus).
# Starts from autostart — restores env vars COSMIC/desktop files don’t reliably inherit vs an interactive terminal.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# systemd --user define INVOCATION_ID; dá tempo do COSMIC subir sockets Wayland + D-Bus.
if [[ -n "${INVOCATION_ID:-}" ]]; then sleep 10; else sleep 2; fi

_import_systemd_user_env() {
  local line key
  while IFS= read -r line; do
    [[ "$line" == *=* ]] || continue
    key="${line%%=*}"
    case "$key" in
      WAYLAND_DISPLAY|XDG_RUNTIME_DIR|DBUS_SESSION_BUS_ADDRESS|DISPLAY|PATH)
        export "$line"
        ;;
    esac
  done < <(systemctl --user show-environment 2>/dev/null || true)
}
_import_systemd_user_env

# Sessão gráfica atual: valores do loginctl batem com o terminal; systemd --user às vezes
# mantém WAYLAND_DISPLAY/DBUS antigos ou genéricos e o GTK entra “meio funcionando”.
_import_loginctl_env_override_graphics() {
  local line key v
  while IFS= read -r line; do
    [[ "$line" == *=* ]] || continue
    key="${line%%=*}"
    case "$key" in
      WAYLAND_DISPLAY|XDG_RUNTIME_DIR|DBUS_SESSION_BUS_ADDRESS|DISPLAY)
        v="${line#*=}"
        [[ -n "$v" ]] || continue
        export "$line"
        ;;
      # PATH não sobrescrevemos — pode quebrar localização do python3/interpreter.
    esac
  done < <(loginctl show-environment 2>/dev/null || true)
}
_import_loginctl_env_override_graphics

XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export XDG_RUNTIME_DIR

if [[ -z "${WAYLAND_DISPLAY:-}" ]]; then
  shopt -s nullglob
  for _ in $(seq 1 90); do
    for sock in "$XDG_RUNTIME_DIR"/wayland-*; do
      [[ -S "$sock" || -e "$sock" ]] || continue
      export WAYLAND_DISPLAY="${sock##*/}"
      break 2
    done
    sleep 1
  done
fi

if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
  unset DISPLAY 2>/dev/null || true
  export GDK_BACKEND="${GDK_BACKEND:-wayland}"
else
  export GDK_BACKEND="${GDK_BACKEND:-x11}"
fi

if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]] && [[ -e "$XDG_RUNTIME_DIR/bus" ]]; then
  export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
fi

if command -v dbus-update-activation-environment >/dev/null 2>&1; then
  dbus-update-activation-environment WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS \
    >/dev/null 2>&1 || true
fi

if [[ "${WIDGET_DEBUG:-}" == "1" ]]; then
  { date -Is; env | sort; echo "---"; } >> /tmp/widget-launch-env.log
fi

if [[ -z "${WAYLAND_DISPLAY:-}" ]]; then
  echo "desktop-widget: aviso — WAYLAND_DISPLAY vazio ao iniciar; interface pode falhar" >&2
fi

exec python3 "$SCRIPT_DIR/main.py"
