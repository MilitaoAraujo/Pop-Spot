"""Plugin do bloco Mídia/Spotify para a UI em GTK (Linux)."""

from __future__ import annotations

import logging
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

import config as cfg
import spotify as mod_spotify
from config import (
    ICONE_SPOTIFY_ANTERIOR,
    ICONE_SPOTIFY_PAUSAR,
    ICONE_SPOTIFY_PROXIMO,
    ICONE_SPOTIFY_REPRODUZIR,
)
from config.i18n import t

from .base import BaseWidgetPlugin

__all__ = ["MidiaPlugin", "BotaoMedia"]

log = logging.getLogger("widget.midia")

_ESCALA_MIN = 0.80
_ESCALA_MAX = 1.30


def _escala_f() -> float:
    try:
        return max(_ESCALA_MIN, min(_ESCALA_MAX, float(cfg.ESCALA)))
    except Exception:
        return 1.0


def _px(n: float) -> int:
    return max(1, int(round(float(n) * _escala_f())))


class BotaoMedia(Gtk.Button):
    """Controles prev/play/pause/next — Gtk.Button (visível sem python3-gi-cairo)."""

    _ICONES = {
        "play": ICONE_SPOTIFY_REPRODUZIR,
        "pause": ICONE_SPOTIFY_PAUSAR,
        "prev": ICONE_SPOTIFY_ANTERIOR,
        "next": ICONE_SPOTIFY_PROXIMO,
    }

    def __init__(self, tipo: str, tooltip: str):
        super().__init__()
        self._tipo = tipo
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_focus_on_click(False)
        self.set_tooltip_text(tooltip)
        self.get_style_context().add_class("btnSpotify")
        self.set_sensitive(False)
        self._atualizar_label()

    def definir_tamanho(self, w: int, h: int):
        self.set_size_request(w, h)

    def set_tipo(self, tipo: str):
        self._tipo = tipo
        self._atualizar_label()

    def set_habilitado(self, v: bool):
        self.set_sensitive(v)

    def _atualizar_label(self):
        self.set_label(self._ICONES.get(self._tipo, ""))


class MidiaPlugin(BaseWidgetPlugin):
    id = "midia"
    nome = "Mídia/Spotify"

    def __init__(self) -> None:
        super().__init__()
        self.ocupado = False
        self.url_capa_atual = None
        self.volume_syncing = False

    def on_mount(self, host) -> Gtk.Box:
        self.host = host
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        linha_cabecalho = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.img_nota = Gtk.Image()
        self.img_nota.set_valign(Gtk.Align.CENTER)
        self.atualizar_nota()
        self.lbl_cabecalho = host._rotulo("cabecalhoSpotify", t("playing"), Gtk.Align.START)
        linha_cabecalho.pack_start(self._tornar_clicavel(self.img_nota), False, False, 0)
        linha_cabecalho.pack_start(self.lbl_cabecalho, False, False, 0)
        caixa.pack_start(linha_cabecalho, False, False, 0)

        self.img_capa = Gtk.Image()
        self.img_capa.set_size_request(_px(cfg.TAMANHO_CAPA), _px(cfg.TAMANHO_CAPA))
        envoltorio_capa = self._tornar_clicavel(self.img_capa)
        envoltorio_capa.set_halign(Gtk.Align.START)
        caixa.pack_start(envoltorio_capa, False, False, 8)

        linha_ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        linha_ctrl.set_halign(Gtk.Align.START)
        self.btn_prev = BotaoMedia("prev", t("prev_track"))
        self.btn_prev.connect("clicked", self.on_prev)
        self.btn_play = BotaoMedia("play", t("play"))
        self.btn_play.connect("clicked", self.on_play_pause)
        self.btn_next = BotaoMedia("next", t("next_track"))
        self.btn_next.connect("clicked", self.on_next)
        for b in (self.btn_prev, self.btn_play, self.btn_next):
            linha_ctrl.pack_start(b, False, False, 0)

        self.scale_volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale_volume.set_draw_value(False)
        self.scale_volume.set_size_request(88, -1)
        self.scale_volume.set_valign(Gtk.Align.CENTER)
        self.scale_volume.set_tooltip_text(t("volume"))
        self.scale_volume.get_style_context().add_class("scaleVolume")
        self.scale_volume.set_sensitive(False)
        self.scale_volume.connect("value-changed", self.on_volume_changed)
        host._ignorar_scroll_scale(self.scale_volume)
        linha_ctrl.pack_start(self.scale_volume, False, False, 4)

        caixa.pack_start(linha_ctrl, False, False, 8)

        self.lbl_titulo = host._rotulo("tituloMusica", "", Gtk.Align.START, reticencias=True)
        self.lbl_artista = host._rotulo("artistaMusica", "", Gtk.Align.START, reticencias=True)
        self.lbl_album = host._rotulo("albumMusica", "", Gtk.Align.START, reticencias=True)
        self.lbl_sem_musica = host._rotulo("semMusica", t("no_spotify"), Gtk.Align.START)

        caixa_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for w in (self.lbl_titulo, self.lbl_artista, self.lbl_album):
            caixa_info.pack_start(w, False, False, 0)

        # O espectro de áudio é construído e gerenciado pelo host (plugin próprio
        # ainda não existe), mas visualmente fica ao lado das infos da música.
        linha_musica = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        linha_musica.pack_start(caixa_info, True, True, 0)
        linha_musica.pack_start(host.espectro_area, False, False, 0)

        caixa.pack_start(linha_musica, False, False, 0)
        caixa.pack_start(self.lbl_sem_musica, False, False, 0)

        self.widget = caixa
        return caixa

    def _tornar_clicavel(self, widget):
        """Envolve um widget num EventBox clicável, sem disparar arrasto da janela."""
        box = Gtk.EventBox()
        box.set_visible_window(False)
        box.add(widget)
        box._pop_spot_no_drag = True
        box.connect("button-press-event", self._on_clique)
        return box

    def _on_clique(self, _widget, event):
        if event.button == 1:
            threading.Thread(target=mod_spotify.abrir, daemon=True).start()
            return True
        return False

    def atualizar_nota(self) -> None:
        try:
            from weather_icons import renderizar_nota

            self.img_nota.set_from_pixbuf(renderizar_nota(tamanho=_px(16), cor=cfg.COR_DESTAQUE))
        except Exception as e:
            log.debug("nota spotify: %s", e)

    def tick(self) -> bool:
        if self.ocupado:
            return True
        self.ocupado = True
        threading.Thread(target=self._bg, daemon=True).start()
        return True

    def _bg(self) -> None:
        try:
            dados = mod_spotify.buscar_faixa()
            GLib.idle_add(self.aplicar, dados)
        finally:
            self.ocupado = False

    def refresh_once(self) -> bool:
        self.tick()
        return False

    def on_prev(self, _widget=None) -> None:
        if mod_spotify.comando("Previous"):
            GLib.timeout_add(200, self.refresh_once)

    def on_next(self, _widget=None) -> None:
        if mod_spotify.comando("Next"):
            GLib.timeout_add(200, self.refresh_once)

    def on_play_pause(self, _widget=None) -> None:
        if mod_spotify.comando("PlayPause"):
            GLib.timeout_add(200, self.refresh_once)

    def on_volume_changed(self, scale) -> None:
        if self.volume_syncing:
            return
        vol = scale.get_value() / 100.0
        threading.Thread(target=mod_spotify.definir_volume, args=(vol,), daemon=True).start()

    def aplicar(self, dados) -> bool:
        tocando = dados and dados["status"] in ("Playing", "Running")
        pausado = dados and dados["status"] == "Paused"

        spotify_aberto = bool(dados)
        for b in (self.btn_prev, self.btn_play, self.btn_next):
            b.set_habilitado(spotify_aberto)
        self.scale_volume.set_sensitive(spotify_aberto and dados.get("volume") is not None)
        if dados and dados.get("volume") is not None:
            self.volume_syncing = True
            try:
                self.scale_volume.set_value(max(0.0, min(100.0, float(dados["volume"]) * 100)))
            finally:
                self.volume_syncing = False
        if dados:
            self.btn_play.set_tipo("pause" if tocando else "play")
            self.btn_play.set_tooltip_text(t("pause") if tocando else t("play"))

        self.lbl_sem_musica.set_visible(not spotify_aberto)
        self.lbl_cabecalho.set_text((t("paused") if pausado else t("playing")) if dados else "")

        if tocando or pausado:
            prefixo = cfg.PREFIXO_PAUSADO if pausado else ""
            self.lbl_titulo.set_text(prefixo + dados["titulo"])
            self.lbl_artista.set_text(dados["artista"])
            self.lbl_album.set_text(dados["album"])
            capa = dados["capa"]
            if capa and capa != self.url_capa_atual:
                self.url_capa_atual = capa
                threading.Thread(target=self._bg_capa, args=(capa,), daemon=True).start()
        # Quando Spotify está fechado (dados is None), mantém capa e textos da
        # última música — não limpa nada, o usuário vê a última faixa ouvida.
        return False

    def _bg_capa(self, url) -> None:
        pb = mod_spotify.carregar_capa(url, _px(cfg.TAMANHO_CAPA))
        GLib.idle_add(self._aplicar_capa, pb)

    def _aplicar_capa(self, pb) -> bool:
        if pb:
            self.img_capa.set_from_pixbuf(pb)
        return False

    def recarregar_capa_atual(self) -> None:
        """Rebusca a capa já conhecida (ex.: após troca de tema/escala)."""
        if self.url_capa_atual:
            threading.Thread(target=self._bg_capa, args=(self.url_capa_atual,), daemon=True).start()

    def on_theme_change(self, cores) -> None:
        self.atualizar_nota()
