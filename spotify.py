# Integração com Spotify / player de mídia
# Linux: D-Bus MPRIS2 | Windows: Windows Media Session API (winsdk)
import sys
import logging
import requests
from gi.repository import GdkPixbuf

log = logging.getLogger("widget.spotify")


# ── Backend Linux: D-Bus MPRIS2 ───────────────────────────────────────────────

def _obj_mpris():
    try:
        import dbus
        bus = dbus.SessionBus()
        for name in bus.list_names():
            if "spotify" in name.lower():
                return bus.get_object(name, "/org/mpris/MediaPlayer2")
        return None
    except Exception as e:
        log.debug("objeto MPRIS Spotify: %s", e)
        return None


def _comando_linux(metodo: str) -> bool:
    obj = _obj_mpris()
    if not obj:
        return False
    try:
        import dbus
        player = dbus.Interface(obj, "org.mpris.MediaPlayer2.Player")
        getattr(player, metodo)()
        return True
    except Exception as e:
        log.warning("comando MPRIS %s falhou: %s", metodo, e)
        return False


def _buscar_linux() -> dict | None:
    obj = _obj_mpris()
    if not obj:
        return None
    try:
        import dbus
        props  = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
        meta   = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")
        return {
            "status":  status,
            "titulo":  str(meta.get("xesam:title",  "")),
            "artista": ", ".join(str(a) for a in meta.get("xesam:artist", [])),
            "album":   str(meta.get("xesam:album",  "")),
            "capa":    str(meta.get("mpris:artUrl", "")),
        }
    except Exception as e:
        log.warning("erro ao buscar Spotify (Linux): %s", e)
        return None


# ── Backend Windows: título da janela + teclas de mídia (sem pacotes extras) ──

def _proc_name(pid: int) -> str:
    """Retorna o nome do executável do processo (ex: 'Spotify.exe')."""
    import ctypes
    import ctypes.wintypes
    try:
        PROCESS_QUERY_LIMITED = 0x1000
        hproc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
        if not hproc:
            return ""
        buf  = ctypes.create_unicode_buffer(512)
        size = ctypes.wintypes.DWORD(512)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(hproc, 0, buf, ctypes.byref(size))
        ctypes.windll.kernel32.CloseHandle(hproc)
        return buf.value.split("\\")[-1].lower()
    except Exception:
        return ""


def _buscar_windows() -> dict | None:
    """Lê artista/título do Spotify via título da janela Win32.
    Prioriza busca por nome de processo; usa classe da janela como fallback."""
    try:
        import ctypes
        import ctypes.wintypes

        # Classes usadas por janelas Spotify / Electron
        SPOTIFY_CLASSES = {"Chrome_WidgetWin_0", "Chrome_WidgetWin_1", "SpotifyMainWindow"}

        encontrado = [None]
        ENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

        def _cb(hwnd, _):
            try:
                n = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if n == 0:
                    return True
                buf = ctypes.create_unicode_buffer(n + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, n + 1)
                titulo = buf.value.strip()
                if not titulo or " - " not in titulo:
                    return True

                # 1) Verifica nome do processo (mais confiável)
                pid = ctypes.wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if "spotify" in _proc_name(pid.value):
                    encontrado[0] = titulo
                    return False   # para a enumeração

                # 2) Fallback: verifica classe da janela (cobre casos em que
                #    QueryFullProcessImageNameW falha por restrições de acesso)
                cls = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(hwnd, cls, 256)
                if cls.value in SPOTIFY_CLASSES:
                    encontrado[0] = titulo
                    return False
            except Exception:
                pass
            return True

        ctypes.windll.user32.EnumWindows(ENUMPROC(_cb), 0)

        titulo_janela = encontrado[0]
        if not titulo_janela or " - " not in titulo_janela:
            return None

        artista, titulo = titulo_janela.split(" - ", 1)
        return {
            "status":  "Playing",
            "titulo":  titulo.strip(),
            "artista": artista.strip(),
            "album":   "",
            "capa":    "",
        }
    except Exception as e:
        log.debug("buscar_windows: %s", e)
        return None


def _comando_windows(metodo: str) -> bool:
    """Envia tecla de mídia virtual (funciona com qualquer player)."""
    try:
        import ctypes
        import ctypes.wintypes

        VK = {"PlayPause": 0xB3, "Next": 0xB0, "Previous": 0xB1}
        vk = VK.get(metodo)
        if not vk:
            return False

        INPUT_KEYBOARD   = 1
        KEYEVENTF_KEYUP  = 0x0002

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", ctypes.wintypes.WORD), ("wScan", ctypes.wintypes.WORD),
                        ("dwFlags", ctypes.wintypes.DWORD), ("time", ctypes.wintypes.DWORD),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

        class _U(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        class INPUT(ctypes.Structure):
            _anonymous_ = ("_u",)
            _fields_    = [("type", ctypes.wintypes.DWORD), ("_u", _U)]

        inputs = (INPUT * 2)()
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].ki.wVk = vk
        inputs[1].type = INPUT_KEYBOARD
        inputs[1].ki.wVk = vk
        inputs[1].ki.dwFlags = KEYEVENTF_KEYUP

        ctypes.windll.user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
        return True
    except Exception as e:
        log.debug("comando_windows: %s", e)
        return False


# ── API pública (usada por window.py) ─────────────────────────────────────────

def comando(metodo: str) -> bool:
    if sys.platform == "win32":
        return _comando_windows(metodo)
    return _comando_linux(metodo)


def buscar_faixa() -> dict | None:
    if sys.platform == "win32":
        return _buscar_windows()
    return _buscar_linux()


def carregar_capa(url: str, tamanho: int) -> GdkPixbuf.Pixbuf | None:
    """Baixa e redimensiona a capa do álbum para um quadrado de `tamanho` px."""
    try:
        if url.startswith("file://"):
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                url[7:], tamanho, tamanho, True
            )
        else:
            dados  = requests.get(url, timeout=10).content
            loader = GdkPixbuf.PixbufLoader()
            loader.write(dados)
            loader.close()
            pb = loader.get_pixbuf()
            if pb:
                pb = pb.scale_simple(tamanho, tamanho, GdkPixbuf.InterpType.BILINEAR)
        return pb
    except Exception as e:
        log.warning("erro ao carregar capa: %s", e)
        return None
