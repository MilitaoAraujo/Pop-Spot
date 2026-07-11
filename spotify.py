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

# Cache de capas: (artista_lower, titulo_lower) → url  (evita chamadas repetidas)
_capa_cache: dict = {}

# Processos conhecidos de media players para fallback (quando Spotify está fechado)
_MEDIA_PROCS = {
    "vlc.exe", "mpv.exe", "wmplayer.exe", "musicbee.exe", "foobar2000.exe",
    "groove.exe", "itunes.exe", "aimp.exe", "winamp.exe", "mpc-hc64.exe",
    "mpc-hc.exe", "mpc-be64.exe", "mpc-be.exe",
    "vivaldi.exe", "chrome.exe", "chromium.exe", "firefox.exe",
    "msedge.exe", "opera.exe", "brave.exe", "waterfox.exe",
    "discord.exe", "discordptb.exe", "discordcanary.exe",
}

# Sufixos de browser/plataforma para remover do título de janela
_SUFIXOS_BROWSER = {
    "youtube", "youtube music", "spotify", "soundcloud", "deezer", "tidal",
    "vivaldi", "google chrome", "mozilla firefox", "microsoft edge", "opera",
    "brave", "chromium", "discord",
}


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


def _capa_itunes(artista: str, titulo: str) -> str:
    """Busca URL da capa na iTunes Search API (sem autenticação, gratuita).
    Resultado fica em cache para evitar chamadas repetidas."""
    chave = (artista.lower(), titulo.lower())
    if chave in _capa_cache:
        return _capa_cache[chave]
    try:
        resp = requests.get(
            "https://itunes.apple.com/search",
            params={"term": f"{artista} {titulo}", "entity": "song", "limit": 1},
            timeout=5,
        )
        data = resp.json()
        if data.get("resultCount", 0) > 0:
            url = data["results"][0].get("artworkUrl100", "")
            url = url.replace("100x100bb", "600x600bb")
            _capa_cache[chave] = url
            return url
    except Exception as e:
        log.debug("itunes capa: %s", e)
    _capa_cache[chave] = ""
    return ""


def _enumerar_janelas(filtro_proc) -> tuple[str | None, str | None]:
    """Enumera janelas visíveis e retorna (titulo_janela, proc_name) para a
    primeira janela cujo título contenha ' - ' e cujo processo passe em filtro_proc."""
    import ctypes
    import ctypes.wintypes

    resultado = [None, None]
    ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

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
            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            nome = _proc_name(pid.value)
            if filtro_proc(nome):
                resultado[0] = titulo
                resultado[1] = nome
                return False
        except Exception:
            pass
        return True

    ctypes.windll.user32.EnumWindows(ENUMPROC(_cb), 0)
    return resultado[0], resultado[1]


def _buscar_windows() -> dict | None:
    """1) Procura Spotify.exe. 2) Fallback: qualquer media player ativo."""

    # ── Spotify ────────────────────────────────────────────────────────────
    titulo_janela, _ = _enumerar_janelas(lambda p: p == "spotify.exe")
    if titulo_janela and " - " in titulo_janela:
        artista, titulo = titulo_janela.split(" - ", 1)
        artista = artista.strip()
        titulo  = titulo.strip()
        capa    = _capa_itunes(artista, titulo)
        return {
            "status":  "Playing",
            "fonte":   "Spotify",
            "titulo":  titulo,
            "artista": artista,
            "album":   "",
            "capa":    capa,
        }

    # ── Fallback: outro player ─────────────────────────────────────────────
    titulo_janela, proc = _enumerar_janelas(lambda p: p in _MEDIA_PROCS)
    if not titulo_janela or " - " not in titulo_janela:
        return None

    # Remove sufixos de plataforma/browser do título
    # Ex: "Fly-day Chinatown - YouTube - Vivaldi" → artista="Fly-day Chinatown", titulo="YouTube"
    partes = [p.strip() for p in titulo_janela.split(" - ")]
    partes_uteis = [p for p in partes if p.lower() not in _SUFIXOS_BROWSER]
    if len(partes_uteis) >= 2:
        titulo  = partes_uteis[0]
        artista = partes_uteis[1]
    elif partes_uteis:
        titulo  = partes_uteis[0]
        artista = ""
    else:
        titulo  = partes[0]
        artista = partes[1] if len(partes) > 1 else ""

    fonte = (proc or "").replace(".exe", "").capitalize()
    capa  = _capa_itunes(artista, titulo) if artista else ""
    return {
        "status":  "Playing",
        "fonte":   fonte,
        "titulo":  titulo,
        "artista": artista,
        "album":   fonte,
        "capa":    capa,
    }


def _comando_windows(metodo: str) -> bool:
    """Envia tecla de mídia virtual via keybd_event (funciona com qualquer player)."""
    try:
        import ctypes
        VK = {"PlayPause": 0xB3, "Next": 0xB0, "Previous": 0xB1}
        vk = VK.get(metodo)
        if not vk:
            return False
        KEYEVENTF_KEYUP = 0x02
        ctypes.windll.user32.keybd_event(vk, 0, 0,              0)
        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
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
