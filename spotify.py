# Integração com Spotify via D-Bus MPRIS2
import logging
import subprocess
import requests
from gi.repository import GdkPixbuf

log = logging.getLogger("widget.spotify")


def _obj_mpris():
    try:
        import dbus
        bus = dbus.SessionBus()
        for name in bus.list_names():
            if "spotify" in name.lower():
                return bus.get_object(name, "/org/mpris/MediaPlayer2")
    except Exception as e:
        log.debug("MPRIS: %s", e)
    return None


def _props():
    obj = _obj_mpris()
    if not obj:
        return None, None
    try:
        import dbus
        return obj, dbus.Interface(obj, "org.freedesktop.DBus.Properties")
    except Exception:
        return None, None


def comando(metodo: str) -> bool:
    obj = _obj_mpris()
    if not obj:
        return False
    try:
        import dbus
        getattr(dbus.Interface(obj, "org.mpris.MediaPlayer2.Player"), metodo)()
        return True
    except Exception as e:
        log.warning("MPRIS %s: %s", metodo, e)
        return False


def obter_volume() -> float | None:
    """Volume MPRIS 0.0–1.0, ou None se indisponível."""
    _obj, props = _props()
    if not props:
        return None
    try:
        return float(props.Get("org.mpris.MediaPlayer2.Player", "Volume"))
    except Exception as e:
        log.debug("volume get: %s", e)
        return None


def definir_volume(valor: float) -> bool:
    """Define volume MPRIS (0.0–1.0)."""
    _obj, props = _props()
    if not props:
        return False
    try:
        import dbus
        v = max(0.0, min(1.0, float(valor)))
        props.Set("org.mpris.MediaPlayer2.Player", "Volume", dbus.Double(v))
        return True
    except Exception as e:
        log.debug("volume set: %s", e)
        return False


def abrir() -> bool:
    """Traz o Spotify pra frente ou abre o app."""
    obj = _obj_mpris()
    if obj:
        try:
            import dbus
            dbus.Interface(obj, "org.mpris.MediaPlayer2").Raise()
            return True
        except Exception:
            pass
    try:
        subprocess.Popen(
            ["xdg-open", "spotify:"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except Exception as e:
        log.warning("abrir Spotify: %s", e)
        return False


def buscar_faixa() -> dict | None:
    obj, props = _props()
    if not obj or not props:
        return None
    try:
        status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
        meta = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")
        try:
            volume = float(props.Get("org.mpris.MediaPlayer2.Player", "Volume"))
        except Exception:
            volume = None
        return {
            "status": status,
            "titulo": str(meta.get("xesam:title", "")),
            "artista": ", ".join(str(a) for a in meta.get("xesam:artist", [])),
            "album": str(meta.get("xesam:album", "")),
            "capa": str(meta.get("mpris:artUrl", "")),
            "volume": volume,
        }
    except Exception as e:
        log.warning("Spotify: %s", e)
        return None


def carregar_capa(url: str, tamanho: int) -> GdkPixbuf.Pixbuf | None:
    try:
        if url.startswith("file://"):
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(url[7:], tamanho, tamanho, True)
        dados = requests.get(url, timeout=10).content
        loader = GdkPixbuf.PixbufLoader()
        loader.write(dados)
        loader.close()
        pb = loader.get_pixbuf()
        return pb.scale_simple(tamanho, tamanho, GdkPixbuf.InterpType.BILINEAR) if pb else None
    except Exception as e:
        log.warning("capa: %s", e)
        return None
