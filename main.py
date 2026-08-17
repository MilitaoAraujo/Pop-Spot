# Widget de Desktop — Relógio, Clima e Spotify
#
# Personalize em config/:
#   colors.py, layout.py, general.py, personalizar.py, themes.py

import sys
import os
import fcntl
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.WARNING)

from window import WidgetDesktop

_lock_fp = None


def _uma_instancia():
    """Garante um único processo (lock em XDG_RUNTIME_DIR)."""
    global _lock_fp
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp")
    arq = runtime / "pop-spot.lock"
    _lock_fp = open(arq, "w")
    try:
        fcntl.flock(_lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        try:
            from config.i18n import t
            print(t("already_running"), file=sys.stderr)
        except Exception:
            print("Pop Spot is already running.", file=sys.stderr)
        sys.exit(0)
    _lock_fp.write(str(os.getpid()))
    _lock_fp.flush()


def main():
    _uma_instancia()
    WidgetDesktop().show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
