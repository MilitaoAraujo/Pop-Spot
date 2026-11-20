"""Plugin do bloco Espectro (visualizador de áudio) para a UI em Qt/PySide6 (Windows)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

import config as cfg
from spectrum import N_BARS, AudioSpectrum

from .base import BaseWidgetPlugin

__all__ = ["EspectroPlugin", "EspectroBarras"]


class EspectroBarras(QWidget):
    def __init__(self, n: int = N_BARS, altura: int = 55, largura: int = 95):
        super().__init__()
        self._n = n
        self._levels = [0.0] * n
        self.definir_tamanho(largura, altura)

    def definir_tamanho(self, largura: int, altura: int):
        self._altura = max(8, int(altura))
        self.setFixedSize(max(20, int(largura)), self._altura)

    def set_levels(self, levels):
        self._levels = [max(0.0, min(1.0, float(v))) for v in (levels or [])]
        while len(self._levels) < self._n:
            self._levels.append(0.0)
        self.update()

    def paintEvent(self, event):
        from config import COR_DESTAQUE

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(COR_DESTAQUE))
        n = self._n
        w, h = self.width(), self.height()
        gap = 2
        bw = max(2, int((w - gap * (n - 1)) / n))
        for i, v in enumerate(self._levels[:n]):
            bh = max(2, int(h * v))
            x = i * (bw + gap)
            p.drawRoundedRect(x, h - bh, bw, bh, 1, 1)


class EspectroPlugin(BaseWidgetPlugin):
    id = "espectro"
    nome = "Espectro"

    def __init__(self) -> None:
        super().__init__()
        self.motor = AudioSpectrum()

    def on_mount(self, host) -> QWidget:
        self.host = host
        from win.scale import px

        self.area = EspectroBarras(altura=px(55), largura=px(95))
        self.widget = self.area
        return self.area

    def tick(self) -> None:
        if bool(getattr(cfg, "MOSTRAR_ESPECTRO", True)):
            self.area.set_levels(self.motor.get_bars())

    def aplicar_visibilidade(self) -> None:
        ligado = bool(getattr(cfg, "MOSTRAR_ESPECTRO", True))
        self.area.setVisible(ligado)
        if ligado:
            self.motor.start()
        else:
            self.motor.stop()
            self.area.set_levels([0.0] * N_BARS)

    def redimensionar(self, largura: int, altura: int) -> None:
        self.area.definir_tamanho(largura, altura)

    def parar(self) -> None:
        self.motor.stop()
