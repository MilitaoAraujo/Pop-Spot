"""Plugin do bloco Mídia/Spotify para a UI em Qt/PySide6 (Windows)."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from config.i18n import t
from win.icons import pix_media, pix_nota
from win.scale import px

from .base import BaseWidgetPlugin

__all__ = ["MidiaPlugin"]

log = logging.getLogger("widget.midia")


class MidiaPlugin(BaseWidgetPlugin):
    id = "midia"
    nome = "Mídia/Spotify"

    def __init__(self) -> None:
        super().__init__()
        self.ocupado = False
        self.tocando = False
        self.url_capa = None
        self.volume_sync = False

    def on_mount(self, host) -> QWidget:
        self.host = host
        from config import TAMANHO_CAPA

        caixa = QWidget()
        sp = QVBoxLayout(caixa)
        sp.setContentsMargins(0, 0, 0, 0)
        sp.setSpacing(0)

        self.lbl_cabecalho = host._rotulo("cabecalhoSpotify", t("playing"))
        cab = QHBoxLayout()
        cab.setSpacing(px(5))
        self.img_nota = QLabel()
        self.img_nota.setFixedSize(px(16), px(16))
        self.atualizar_nota()
        cab.addWidget(self.img_nota, 0, Qt.AlignmentFlag.AlignVCenter)
        cab.addWidget(self.lbl_cabecalho, 0, Qt.AlignmentFlag.AlignVCenter)
        cab.addStretch(1)
        sp.addLayout(cab)

        self.btn_capa = QPushButton()
        self.btn_capa.setObjectName("btnCapa")
        self.btn_capa.setFixedSize(px(TAMANHO_CAPA), px(TAMANHO_CAPA))
        self.btn_capa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_capa.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_capa.clicked.connect(self.abrir)
        sp.addSpacing(px(8))
        sp.addWidget(self.btn_capa, 0, Qt.AlignmentFlag.AlignLeft)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(px(4))
        ctrl.setContentsMargins(0, 0, 0, 0)
        self.btn_prev = QPushButton()
        self.btn_play = QPushButton()
        self.btn_next = QPushButton()
        for b, tip, tipo in (
            (self.btn_prev, t("prev_track"), "prev"),
            (self.btn_play, t("play"), "play"),
            (self.btn_next, t("next_track"), "next"),
        ):
            b.setObjectName("btnSpotify")
            b.setToolTip(tip)
            b.setEnabled(False)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setMaximumWidth(px(52))
            b.setIconSize(QSize(px(15), px(15)))
            self._definir_icone(b, tipo)
            ctrl.addWidget(b, 0)
        self.btn_prev.clicked.connect(lambda: self.comando("Previous"))
        self.btn_play.clicked.connect(self.play_pause)
        self.btn_next.clicked.connect(lambda: self.comando("Next"))

        self.scale_volume = QSlider(Qt.Orientation.Horizontal)
        self.scale_volume.setObjectName("scaleVolume")
        self.scale_volume.setRange(0, 100)
        self.scale_volume.setMinimumHeight(px(28))
        self.scale_volume.setMinimumWidth(px(64))
        self.scale_volume.setEnabled(False)
        self.scale_volume.setToolTip(t("volume"))
        self.scale_volume.valueChanged.connect(self.on_volume)
        ctrl.addWidget(self.scale_volume, 1)
        sp.addSpacing(px(8))
        sp.addLayout(ctrl)

        self.lbl_titulo = host._rotulo("tituloMusica")
        self.lbl_artista = host._rotulo("artistaMusica")
        self.lbl_album = host._rotulo("albumMusica")
        self.lbl_sem_musica = host._rotulo("semMusica", t("no_spotify"))
        self.img_status = QLabel()
        self.img_status.setObjectName("statusMusica")
        self.img_status.setFixedSize(px(13), px(13))
        self.img_status.hide()

        caixa_info = QVBoxLayout()
        caixa_info.setContentsMargins(0, 0, 0, 0)
        caixa_info.setSpacing(0)
        caixa_info.addSpacing(px(12))
        linha_titulo = QHBoxLayout()
        linha_titulo.setContentsMargins(0, 0, 0, 0)
        linha_titulo.setSpacing(px(5))
        linha_titulo.addWidget(self.img_status, 0, Qt.AlignmentFlag.AlignVCenter)
        linha_titulo.addWidget(self.lbl_titulo, 1, Qt.AlignmentFlag.AlignVCenter)
        caixa_info.addLayout(linha_titulo)
        caixa_info.addWidget(self.lbl_artista)
        caixa_info.addWidget(self.lbl_album)

        # O espectro de áudio é construído e gerenciado pelo host (plugin próprio
        # ainda não existe), mas visualmente fica ao lado das infos da música.
        linha_musica = QHBoxLayout()
        linha_musica.setSpacing(px(10))
        linha_musica.addLayout(caixa_info, 1)
        linha_musica.addWidget(host.espectro_area, 0, Qt.AlignmentFlag.AlignVCenter)
        sp.addLayout(linha_musica)
        sp.addWidget(self.lbl_sem_musica)

        self.widget = caixa
        return caixa

    def _definir_icone(self, botao: QPushButton, tipo: str) -> None:
        from config import COR_DESTAQUE, COR_TEXTO_APAGADO

        tamanho = px(15)
        icone = QIcon()
        icone.addPixmap(pix_media(tipo, tamanho, COR_DESTAQUE), QIcon.Mode.Normal)
        icone.addPixmap(pix_media(tipo, tamanho, COR_TEXTO_APAGADO), QIcon.Mode.Disabled)
        botao.setIcon(icone)

    def atualizar_nota(self) -> None:
        from config import COR_DESTAQUE

        self.img_nota.setPixmap(pix_nota(px(16), COR_DESTAQUE))

    def tick(self) -> None:
        if self.ocupado:
            return
        self.ocupado = True
        threading.Thread(target=self._bg, daemon=True).start()

    def _bg(self) -> None:
        try:
            import spotify as mod

            dados = mod.buscar_faixa()
        except Exception as e:
            log.debug("spotify: %s", e)
            dados = None
        self.host.spotify_pronto.emit(dados)

    def comando(self, metodo: str) -> None:
        threading.Thread(target=lambda: __import__("spotify").comando(metodo), daemon=True).start()
        QTimer.singleShot(300, self.tick)

    def play_pause(self) -> None:
        self.comando("PlayPause")

    def abrir(self) -> None:
        threading.Thread(target=lambda: __import__("spotify").abrir(), daemon=True).start()

    def on_volume(self, valor: int) -> None:
        if self.volume_sync:
            return
        v = max(0.0, min(1.0, valor / 100.0))
        threading.Thread(target=lambda: __import__("spotify").definir_volume(v), daemon=True).start()

    def aplicar(self, dados) -> None:
        self.ocupado = False
        ativo = bool(dados and dados.get("titulo"))
        for b in (self.btn_prev, self.btn_play, self.btn_next):
            b.setEnabled(ativo)
        self.scale_volume.setEnabled(ativo and dados.get("volume") is not None)
        if not ativo:
            self.lbl_sem_musica.show()
            self.lbl_titulo.hide()
            self.lbl_artista.hide()
            self.lbl_album.hide()
            self.img_status.hide()
            self.lbl_cabecalho.setText(t("playing"))
            self.btn_capa.setIcon(QIcon())
            self.url_capa = None
            return
        self.lbl_sem_musica.hide()
        self.lbl_titulo.show()
        self.lbl_artista.show()
        self.lbl_album.show()
        tocando = str(dados.get("status") or "") == "Playing"
        self.tocando = tocando
        self.lbl_cabecalho.setText(t("playing") if tocando else t("paused"))
        self._definir_icone(self.btn_play, "pause" if tocando else "play")
        self.btn_play.setToolTip(t("pause") if tocando else t("play"))
        if tocando:
            self.img_status.hide()
        else:
            from config import COR_DESTAQUE

            self.img_status.setPixmap(pix_media("pause", px(13), COR_DESTAQUE))
            self.img_status.show()
        self.lbl_titulo.setText(str(dados.get("titulo") or ""))
        self.lbl_artista.setText(str(dados.get("artista") or ""))
        self.lbl_album.setText(str(dados.get("album") or ""))
        vol = dados.get("volume")
        if vol is not None and getattr(self.host, "_slider_ativo", None) is not self.scale_volume:
            self.volume_sync = True
            self.scale_volume.setValue(int(round(float(vol) * 100)))
            self.volume_sync = False
        capa = str(dados.get("capa") or "")
        capa_bytes = dados.get("capa_bytes")
        if capa and capa != self.url_capa:
            self.url_capa = capa
            if capa_bytes:
                self.host.capa_pronta.emit(capa_bytes)
            elif capa.startswith(("http://", "https://", "file://")):
                threading.Thread(target=self._bg_capa, args=(capa,), daemon=True).start()
            else:
                # Windows (SMTC): "capa" é só uma chave de mudança de faixa,
                # não uma URL — sem capa_bytes não há thumbnail pra mostrar.
                self.btn_capa.setIcon(QIcon())

    def _bg_capa(self, url: str) -> None:
        try:
            if url.startswith("file://"):
                dados = Path(url[7:]).read_bytes()
            else:
                import requests

                dados = requests.get(url, timeout=10).content
            self.host.capa_pronta.emit(dados)
        except Exception as e:
            log.debug("capa: %s", e)

    def aplicar_capa(self, dados: bytes) -> None:
        from config import TAMANHO_CAPA

        pm = QPixmap()
        if not pm.loadFromData(dados):
            return
        lado = px(TAMANHO_CAPA)
        self.btn_capa.setIcon(
            QIcon(
                pm.scaled(
                    lado,
                    lado,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        )
        self.btn_capa.setIconSize(self.btn_capa.size())

    def on_theme_change(self, cores) -> None:
        self._definir_icone(self.btn_prev, "prev")
        self._definir_icone(self.btn_play, "pause" if self.tocando else "play")
        self._definir_icone(self.btn_next, "next")
        if self.img_status.isVisible():
            from config import COR_DESTAQUE

            self.img_status.setPixmap(pix_media("pause", px(13), COR_DESTAQUE))
        self.atualizar_nota()
