"""Plugin do bloco Espectro (visualizador de áudio) para a UI em GTK (Linux)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import config as cfg
from spectrum import N_BARS, AudioSpectrum

from .base import BaseWidgetPlugin

__all__ = ["EspectroPlugin", "EspectroBarras"]


class EspectroBarras(Gtk.Box):
    """Barras do espectro sem Cairo — EventBox + altura dinâmica."""

    def __init__(self, n: int = N_BARS, altura: int = 55, largura: int = 95):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.set_valign(Gtk.Align.CENTER)
        self._n = n
        self._altura = altura
        self._barras = []
        for _ in range(n):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            spacer = Gtk.Box()
            spacer.set_vexpand(True)
            bar = Gtk.EventBox()
            bar.get_style_context().add_class("specBar")
            bar.set_size_request(4, 2)
            col.pack_start(spacer, True, True, 0)
            col.pack_start(bar, False, False, 0)
            self.pack_start(col, True, True, 0)
            self._barras.append(bar)
        self.definir_tamanho(largura, altura)

    def definir_tamanho(self, largura: int, altura: int):
        self._altura = max(8, int(altura))
        self.set_size_request(max(20, int(largura)), self._altura)

    def set_levels(self, levels):
        h = self._altura
        for bar, v in zip(self._barras, levels):
            px = max(2, int(h * max(0.0, min(1.0, float(v)))))
            bar.set_size_request(4, px)


class EspectroPlugin(BaseWidgetPlugin):
    id = "espectro"
    nome = "Espectro"

    def __init__(self) -> None:
        super().__init__()
        self.motor = AudioSpectrum()

    def on_mount(self, host) -> Gtk.Box:
        self.host = host
        self.area = EspectroBarras()
        self.widget = self.area
        return self.area

    def tick(self) -> bool:
        if cfg.MOSTRAR_ESPECTRO and self.area.get_visible():
            self.area.set_levels(self.motor.get_bars())
        return True

    def aplicar_visibilidade(self) -> None:
        ligado = bool(cfg.MOSTRAR_ESPECTRO)
        self.area.set_visible(ligado)
        if ligado:
            self.motor.start()
        else:
            self.motor.stop()

    def redimensionar(self, largura: int, altura: int) -> None:
        self.area.definir_tamanho(largura, altura)

    def parar(self) -> None:
        self.motor.stop()
