# Runtime hook do PyInstaller — corrige o caminho dos typelibs do GTK
# dentro do executavel gerado. Nao apague este arquivo.
import os
import sys

if getattr(sys, "frozen", False):
    base = sys._MEIPASS
    for sub in ("girepository-1.0", os.path.join("gi", "girepository-1.0")):
        path = os.path.join(base, sub)
        if os.path.isdir(path):
            os.environ.setdefault("GI_TYPELIB_PATH", path)
            break
