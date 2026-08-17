"""Atalho na pasta Inicializar do Windows (abre o widget no login)."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("popspot.win.autostart")

_RAIZ = Path(__file__).resolve().parent.parent
_NOME = "Pop Spot.lnk"


def pasta_startup() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def caminho_atalho() -> Path:
    return pasta_startup() / _NOME


def esta_ligado() -> bool:
    return caminho_atalho().is_file()


def _pythonw() -> Path:
    venv = _RAIZ / ".venv" / "Scripts" / "pythonw.exe"
    if venv.is_file():
        return venv
    exe = Path(sys.executable)
    irmao = exe.with_name("pythonw.exe")
    if irmao.is_file():
        return irmao
    return exe


def ligar() -> bool:
    if sys.platform != "win32":
        return False
    lnk = caminho_atalho()
    lnk.parent.mkdir(parents=True, exist_ok=True)
    alvo = _pythonw()
    script = str(_RAIZ / "main.py")
    ps = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut({json.dumps(str(lnk))}); "
        f"$s.TargetPath = {json.dumps(str(alvo))}; "
        f"$s.Arguments = {json.dumps('"' + script + '"')}; "
        f"$s.WorkingDirectory = {json.dumps(str(_RAIZ))}; "
        "$s.WindowStyle = 7; "
        "$s.Description = 'Pop Spot'; "
        "$s.Save()"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", ps],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if r.returncode != 0 or not lnk.is_file():
            log.warning("autostart: %s %s", r.returncode, (r.stderr or "").strip())
            return False
        return True
    except Exception as e:
        log.warning("autostart ligar: %s", e)
        return False


def desligar() -> bool:
    try:
        caminho_atalho().unlink(missing_ok=True)
        return True
    except Exception as e:
        log.warning("autostart desligar: %s", e)
        return False


if __name__ == "__main__":
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "on").lower()
    if cmd in ("off", "0", "disable"):
        ok = desligar()
    else:
        ok = ligar()
    sys.exit(0 if ok else 1)
