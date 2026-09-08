#!/usr/bin/env python3
"""Pop Spot no Windows (PySide6). No Linux a UI Qt vai numa janela GTK + layer-shell."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

os.chdir(_RAIZ)


def _configurar_logging() -> None:
    """Sempre roda via pythonw (sem console) — sem isso, avisos e erros
    (ex.: falha silenciosa de uma dependência) somem sem deixar rastro.
    Grava em config/popspot.log, com rotação, pra dar pra investigar depois."""
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    raiz.addHandler(console)

    try:
        arq = _RAIZ / "config" / "popspot.log"
        arq.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(arq, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        raiz.addHandler(fh)
    except Exception:
        log = logging.getLogger("popspot.win")
        log.warning("não deu pra abrir o arquivo de log", exc_info=True)


_configurar_logging()


def _uma_instancia():
    from PySide6.QtCore import QLockFile, QStandardPaths

    pasta = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.RuntimeLocation
    ) or os.environ.get("TEMP") or "/tmp"
    lock = QLockFile(str(Path(pasta) / "pop-spot.lock"))
    lock.setStaleLockTime(30_000)
    if not lock.tryLock(100):
        try:
            from config.i18n import t
            print(t("already_running"), file=sys.stderr)
        except Exception:
            print("Pop Spot is already running.", file=sys.stderr)
        sys.exit(0)
    return lock


def main():
    from PySide6.QtWidgets import QApplication

    if sys.platform.startswith("linux"):
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
        os.environ["QT_SCALE_FACTOR"] = "1"
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication(sys.argv)
        app.setApplicationName("Pop Spot")
        from win.host_linux import _usar_gi_do_sistema, run
        _usar_gi_do_sistema()
        run(app, _uma_instancia())
        return

    from PySide6.QtCore import Qt
    from win.native import preparar_plataforma
    from win.window import WidgetWindows

    preparar_plataforma()
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setApplicationName("Pop Spot")
    app.setQuitOnLastWindowClosed(True)
    app._pop_spot_lock = _uma_instancia()
    win = WidgetWindows()
    win.show()
    win.lower()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
