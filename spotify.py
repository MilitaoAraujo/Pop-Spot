# Integração com Spotify via D-Bus (protocolo MPRIS2)
# Spotify integration via D-Bus (MPRIS2 protocol)
import logging
import requests
from gi.repository import GdkPixbuf

log = logging.getLogger("widget.spotify")


def _obj_mpris():
    """Retorna o objeto D-Bus /org/mpris/MediaPlayer2 do Spotify, ou None."""
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


def comando(metodo: str) -> bool:
    """Chama um método do Player MPRIS2: Previous, Next ou PlayPause.

    Retorna True se o comando foi enviado, False se o Spotify não estiver ativo."""
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


def buscar_faixa() -> dict | None:
    """Retorna dict com título, artista, álbum e URL da capa, ou None se o
    Spotify não estiver aberto ou o D-Bus não estiver disponível."""
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
        log.warning("erro ao buscar Spotify: %s", e)
        return None


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
