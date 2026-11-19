"""Mídia no Windows via SMTC (System Media Transport Controls): qualquer player ativo."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess

log = logging.getLogger("popspot.win.media")

_STATUS = {
    0: "Closed",
    1: "Opened",
    2: "Changing",
    3: "Stopped",
    4: "Playing",
    5: "Paused",
}


def _mods():
    try:
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Mgr,
        )
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionPlaybackStatus as St,
        )
        return Mgr, St
    except ImportError:
        pass
    try:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Mgr,
        )
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionPlaybackStatus as St,
        )
        return Mgr, St
    except ImportError:
        return None, None


def _run(coro):
    return asyncio.run(coro)


def _nome_processo_sessao(sessao) -> str:
    """Nome (sem path/extensão) do app por trás da sessão, a partir do AUMID."""
    aumid = (getattr(sessao, "source_app_user_model_id", None) or "")
    base = aumid.replace("\\", "/").rsplit("/", 1)[-1]
    if base.lower().endswith(".exe"):
        base = base[:-4]
    return base.lower()


async def _sessao():
    """Sessão SMTC ativa: prioriza quem está tocando, senão usa a sessão atual do sistema."""
    Mgr, _st = _mods()
    if Mgr is None:
        return None
    mgr = await Mgr.request_async()
    atual = mgr.get_current_session()
    try:
        sessoes = list(mgr.get_sessions())
    except Exception:
        sessoes = [atual] if atual else []
    for s in sessoes:
        if s is None:
            continue
        try:
            if int(s.get_playback_info().playback_status) == 4:
                return s
        except Exception:
            continue
    return atual


async def _thumb_bytes(ref) -> bytes:
    if ref is None:
        return b""
    try:
        stream = await ref.open_read_async()
        size = int(stream.size or 0)
        if size <= 0 or size > 8_000_000:
            return b""
        try:
            from winrt.windows.storage.streams import Buffer, DataReader, InputStreamOptions
        except ImportError:
            from winsdk.windows.storage.streams import Buffer, DataReader, InputStreamOptions
        buf = Buffer(size)
        await stream.read_async(buf, size, InputStreamOptions.NONE)
        try:
            reader = DataReader.from_buffer(buf)
            bruto = reader.read_bytes(size)
            return bytes(bruto)
        except Exception:
            return bytes(buf)
    except Exception as e:
        log.debug("thumb: %s", e)
        return b""


async def _buscar():
    s = await _sessao()
    if s is None:
        return None
    nome_processo = _nome_processo_sessao(s)
    info = s.get_playback_info()
    st = info.playback_status
    status = _STATUS.get(int(st), str(st))
    if hasattr(st, "name"):
        nome = st.name.title()
        if nome in ("Playing", "Paused", "Stopped"):
            status = nome
    props = await s.try_get_media_properties_async()
    if props is None:
        return None
    titulo = str(props.title or "")
    if not titulo:
        return None
    artistas = props.artist or ""
    capa = await _thumb_bytes(props.thumbnail)
    chave = f"{titulo}|{artistas}|{props.album_title or ''}"
    return {
        "status": status,
        "titulo": titulo,
        "artista": str(artistas),
        "album": str(props.album_title or ""),
        "capa": chave,
        "capa_bytes": capa or None,
        "volume": None,
        "_processo": nome_processo,
    }


def _com_init():
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass


def _processo_atual() -> str:
    """Nome do processo (sem .exe) por trás do player de mídia ativo agora."""
    try:
        s = _run(_sessao())
    except Exception:
        return ""
    return _nome_processo_sessao(s) if s else ""


def _sessao_audio_do_processo(sessoes, nome_processo: str):
    for s in sessoes:
        proc = s.Process
        nome = ""
        if proc is not None:
            try:
                nome = (proc.name() or "").lower()
            except Exception:
                nome = ""
        disp = str(getattr(s, "DisplayName", "") or "").lower()
        if nome_processo in nome or nome_processo in disp:
            return s
    return None


def _volume_processo(nome_processo: str):
    """Volume da sessão de áudio do player ativo (0.0–1.0), ou None."""
    if not nome_processo:
        return None
    try:
        from pycaw.pycaw import AudioUtilities
    except ImportError:
        return None
    _com_init()
    try:
        s = _sessao_audio_do_processo(AudioUtilities.GetAllSessions(), nome_processo)
        vol = s.SimpleAudioVolume if s else None
        return float(vol.GetMasterVolume()) if vol else None
    except Exception as e:
        log.debug("pycaw ler: %s", e)
    return None


def _definir_volume_processo(valor: float, nome_processo: str) -> bool:
    if not nome_processo:
        return False
    try:
        from pycaw.pycaw import AudioUtilities
    except ImportError:
        return False
    _com_init()
    alvo = max(0.0, min(1.0, float(valor)))
    try:
        s = _sessao_audio_do_processo(AudioUtilities.GetAllSessions(), nome_processo)
        vol = s.SimpleAudioVolume if s else None
        if vol is None:
            return False
        vol.SetMasterVolume(alvo, None)
        return True
    except Exception as e:
        log.debug("pycaw set: %s", e)
        return False


async def _comando(metodo: str) -> bool:
    _, St = _mods()
    s = await _sessao()
    if s is None:
        return False
    try:
        if metodo == "PlayPause":
            info = s.get_playback_info()
            if St is not None and int(info.playback_status) == 4:
                await s.try_pause_async()
            else:
                nome = getattr(info.playback_status, "name", "")
                if str(nome).upper() == "PLAYING":
                    await s.try_pause_async()
                else:
                    await s.try_play_async()
        elif metodo == "Next":
            await s.try_skip_next_async()
        elif metodo == "Previous":
            await s.try_skip_previous_async()
        elif metodo == "Play":
            await s.try_play_async()
        elif metodo == "Pause":
            await s.try_pause_async()
        else:
            return False
        return True
    except Exception as e:
        log.debug("smtc %s: %s", metodo, e)
        return False


def buscar_faixa() -> dict | None:
    if _mods()[0] is None:
        log.debug("winrt/winsdk SMTC não instalado")
        return None
    try:
        dados = _run(_buscar())
    except Exception as e:
        log.debug("smtc buscar: %s", e)
        return None
    if dados:
        processo = dados.pop("_processo", "")
        dados["volume"] = _volume_processo(processo)
    return dados


def comando(metodo: str) -> bool:
    if _mods()[0] is None:
        return False
    try:
        return _run(_comando(metodo))
    except Exception as e:
        log.debug("smtc comando: %s", e)
        return False


def definir_volume(valor: float) -> bool:
    return _definir_volume_processo(valor, _processo_atual())


def abrir() -> bool:
    try:
        os.startfile("spotify:")  # type: ignore[attr-defined]
        return True
    except Exception:
        pass
    for cmd in (
        ["cmd", "/c", "start", "", "spotify:"],
        ["explorer.exe", "spotify:"],
    ):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            continue
    return False
