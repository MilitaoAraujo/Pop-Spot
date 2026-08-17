#!/usr/bin/env python3
# Pop Spot — UI Qt (PySide6) no Pop!_OS e no Windows.
#
# No Linux a janela Qt é hospedada em GTK + layer-shell (COSMIC precisa disso
# para ficar na mesa, sem dock). A UI em si é a mesma.
# Fallback GTK puro: POPSPOT_GTK=1 python3 main.py

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))
os.chdir(_RAIZ)
logging.basicConfig(level=logging.WARNING)


def main():
    if os.environ.get("POPSPOT_GTK") == "1" and not sys.platform.startswith("win"):
        _main_gtk()
        return
    from win.main import main as win_main
    win_main()


def _main_gtk():
    import fcntl
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    from window import WidgetDesktop

    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp")
    lock_fp = open(runtime / "pop-spot.lock", "w")
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        try:
            from config.i18n import t
            print(t("already_running"), file=sys.stderr)
        except Exception:
            print("Pop Spot is already running.", file=sys.stderr)
        sys.exit(0)
    lock_fp.write(str(os.getpid()))
    lock_fp.flush()
    WidgetDesktop().show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
