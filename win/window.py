"""Janela Qt do Pop Spot — clone visual do widget GTK (página principal)."""

from __future__ import annotations

import calendar
import datetime
import logging
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QAction, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import (
    LARGURA, LADO, MARGEM_DIREITA, POS_X, POS_Y, TAMANHO_CAPA, VERSAO,
    COR_BASE, OPACIDADE_FUNDO, RAIO_BORDA,
    MOSTRAR_CALENDARIO, MOSTRAR_SPOTIFY, MOSTRAR_PREVISAO, MOSTRAR_ESPECTRO,
)
from config.i18n import t
from spectrum import AudioSpectrum, N_BARS
from win.native import aplicar_como_widget
from win.scale import px
from win.style import gerar_qss
from win.settings import PaginaConfig
from win.icons import pix_clima, pix_nota

log = logging.getLogger("popspot.win")

_RAIZ = Path(__file__).resolve().parent.parent
_POS_ARQ = _RAIZ / "config" / ".widget_pos"


class _Painel(QWidget):
    """Fundo arredondado com a cor/opacidade do tema."""

    def paintEvent(self, event):
        from config import COR_BASE, OPACIDADE_FUNDO, RAIO_BORDA
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cor = QColor(COR_BASE)
        cor.setAlphaF(max(0.0, min(1.0, float(OPACIDADE_FUNDO))))
        p.setBrush(cor)
        p.setPen(Qt.PenStyle.NoPen)
        r = px(RAIO_BORDA)
        p.drawRoundedRect(self.rect(), r, r)


class _EspectroBarras(QWidget):
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


class _Stack(QStackedWidget):
    """O stack só ocupa a altura da página visível (como o Gtk.Stack homogeneous=False)."""

    def sizeHint(self):
        w = self.currentWidget()
        return w.sizeHint() if w is not None else super().sizeHint()

    def minimumSizeHint(self):
        w = self.currentWidget()
        return w.minimumSizeHint() if w is not None else super().minimumSizeHint()


class WidgetWindows(QWidget):
    clima_pronto = Signal(object)
    spotify_pronto = Signal(object)
    capa_pronta = Signal(bytes)
    tema_wallpaper = Signal(object, object)

    def __init__(self, janela_nativa: bool = True):
        super().__init__()
        self._janela_nativa = janela_nativa
        self._pos_manual = False
        self._arrastando = False
        self._drag_off = QPoint()
        self._url_capa = None
        self._spotify_ocupado = False
        self._volume_sync = False
        self._slider_ativo = None
        self._cal_dia = -1
        self._previsao_widgets: list[tuple[QLabel, QLabel, QLabel]] = []
        self._espectro = AudioSpectrum()
        self._wall_sig = None

        if janela_nativa:
            self._configurar_janela()
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.setStyleSheet(gerar_qss())
        self._construir_ui()
        self._aplicar_visibilidade()
        self.clima_pronto.connect(self._aplicar_clima, Qt.ConnectionType.QueuedConnection)
        self.spotify_pronto.connect(self._aplicar_spotify, Qt.ConnectionType.QueuedConnection)
        self.capa_pronta.connect(self._aplicar_capa, Qt.ConnectionType.QueuedConnection)
        self.tema_wallpaper.connect(self._aplicar_tema_wallpaper_auto, Qt.ConnectionType.QueuedConnection)
        self._tick_relogio()
        self._ajustar_pagina()
        self._iniciar_timers()
        if janela_nativa:
            QTimer.singleShot(0, self._posicionar)
            QTimer.singleShot(0, self._ligar_sinais_tela)
        QTimer.singleShot(200, self._buscar_clima)

    def _configurar_janela(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowStaysOnBottomHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        util = getattr(Qt.WidgetAttribute, "WA_X11NetWmWindowTypeUtility", None)
        if util is not None:
            self.setAttribute(util, True)
        self.setWindowTitle("Pop Spot")

    def showEvent(self, event):
        super().showEvent(event)
        if self._janela_nativa:
            aplicar_como_widget(self)
            self._conectar_screen(self.screen())

    def _rotulo(self, nome: str, texto: str = "", align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
        lbl = QLabel(texto)
        lbl.setObjectName(nome)
        lbl.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
        lbl.setWordWrap(False)
        return lbl

    def _sep(self) -> QFrame:
        s = QFrame()
        s.setObjectName("sep")
        s.setFrameShape(QFrame.Shape.NoFrame)
        return s

    def _construir_ui(self):
        raiz = _Painel()
        raiz.setObjectName("raiz")
        lay_raiz = QVBoxLayout(raiz)
        pad_v, pad_h = px(26), px(24)
        lay_raiz.setContentsMargins(pad_h, pad_v, pad_h, pad_v)
        lay_raiz.setSpacing(0)

        self._stack = _Stack()
        self._pagina_home = self._pagina_principal()
        self._stack.addWidget(self._pagina_home)
        self._pagina_cfg = PaginaConfig(janela_nativa=self._janela_nativa)
        self._pagina_cfg.salvo.connect(self._apos_salvar)
        self._stack.addWidget(self._pagina_cfg)
        lay_raiz.addWidget(self._stack)

        rodape = QHBoxLayout()
        rodape.addStretch(1)
        self.btn_config = QPushButton("⚙")
        self.btn_config.setObjectName("btnEngrenagem")
        self.btn_config.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_config.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_config.clicked.connect(self._toggle_config)
        rodape.addWidget(self.btn_config, 0, Qt.AlignmentFlag.AlignRight)
        lay_raiz.addSpacing(px(10))
        lay_raiz.addLayout(rodape)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(raiz)
        self._pad_h = pad_h
        self.setFixedWidth(self._largura_janela())
        self._ajustar_pagina()

    def _pagina_principal(self) -> QWidget:
        pagina = QWidget()
        col = QVBoxLayout(pagina)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        relogio_linha = QHBoxLayout()
        relogio_linha.setSpacing(px(12))
        relogio_linha.setAlignment(Qt.AlignmentFlag.AlignTop)
        caixa_clock = QVBoxLayout()
        caixa_clock.setSpacing(0)
        self.lbl_hora = self._rotulo("hora", "00")
        self.lbl_minuto = self._rotulo("minuto", "00")
        self.lbl_diasem = self._rotulo("diaSemana")
        self.lbl_data = self._rotulo("dataCompleta")
        for w in (self.lbl_hora, self.lbl_minuto, self.lbl_diasem, self.lbl_data):
            caixa_clock.addWidget(w)
        relogio_linha.addLayout(caixa_clock, 1)
        relogio_linha.addWidget(self._painel_dir())
        col.addLayout(relogio_linha)
        col.addWidget(self._sep())

        linha_temp = QHBoxLayout()
        linha_temp.setSpacing(px(6))
        self.img_icone_clima = QLabel()
        self.img_icone_clima.setFixedSize(px(36), px(36))
        self._codigo_clima_atual = None
        self._atualizar_icone_clima(None)
        self.lbl_temperatura = self._rotulo("temperaturaClima", "--°C")
        linha_temp.addWidget(self.img_icone_clima, 0, Qt.AlignmentFlag.AlignVCenter)
        linha_temp.addWidget(self.lbl_temperatura, 0, Qt.AlignmentFlag.AlignVCenter)
        linha_temp.addStretch(1)
        col.addLayout(linha_temp)
        self.lbl_cidade = self._rotulo("cidadeClima", "--")
        self.lbl_descricao = self._rotulo("descricaoClima", t("seeking_weather"))
        self.lbl_detalhe = self._rotulo("detalheClima")
        col.addWidget(self.lbl_cidade)
        col.addWidget(self.lbl_descricao)
        col.addWidget(self.lbl_detalhe)
        col.addSpacing(px(6))
        self._caixa_previsao = self._construir_previsao()
        col.addWidget(self._caixa_previsao)
        col.addWidget(self._sep())

        self._caixa_spotify = QWidget()
        sp = QVBoxLayout(self._caixa_spotify)
        sp.setContentsMargins(0, 0, 0, 0)
        sp.setSpacing(0)
        self.lbl_cabecalho_spotify = self._rotulo("cabecalhoSpotify", t("playing"))
        cab = QHBoxLayout()
        cab.setSpacing(px(5))
        self.img_nota_spotify = QLabel()
        self.img_nota_spotify.setFixedSize(px(16), px(16))
        self._atualizar_nota_spotify()
        cab.addWidget(self.img_nota_spotify, 0, Qt.AlignmentFlag.AlignVCenter)
        cab.addWidget(self.lbl_cabecalho_spotify, 0, Qt.AlignmentFlag.AlignVCenter)
        cab.addStretch(1)
        sp.addLayout(cab)
        self.btn_capa = QPushButton()
        self.btn_capa.setObjectName("btnCapa")
        self.btn_capa.setFixedSize(px(TAMANHO_CAPA), px(TAMANHO_CAPA))
        self.btn_capa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_capa.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_capa.clicked.connect(self._abrir_spotify)
        sp.addSpacing(px(8))
        sp.addWidget(self.btn_capa, 0, Qt.AlignmentFlag.AlignLeft)
        ctrl = QHBoxLayout()
        ctrl.setSpacing(px(4))
        ctrl.setContentsMargins(0, 0, 0, 0)
        self.btn_spotify_prev = QPushButton("⏮")
        self.btn_spotify_play = QPushButton("▶")
        self.btn_spotify_next = QPushButton("⏭")
        for b, tip in (
            (self.btn_spotify_prev, t("prev_track")),
            (self.btn_spotify_play, t("play")),
            (self.btn_spotify_next, t("next_track")),
        ):
            b.setObjectName("btnSpotify")
            b.setToolTip(tip)
            b.setEnabled(False)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setMaximumWidth(px(52))
            ctrl.addWidget(b, 0)
        self.btn_spotify_prev.clicked.connect(lambda: self._spotify_cmd("Previous"))
        self.btn_spotify_play.clicked.connect(self._spotify_play_pause)
        self.btn_spotify_next.clicked.connect(lambda: self._spotify_cmd("Next"))
        self.scale_volume = QSlider(Qt.Orientation.Horizontal)
        self.scale_volume.setObjectName("scaleVolume")
        self.scale_volume.setRange(0, 100)
        self.scale_volume.setMinimumHeight(px(28))
        self.scale_volume.setMinimumWidth(px(64))
        self.scale_volume.setEnabled(False)
        self.scale_volume.setToolTip(t("volume"))
        self.scale_volume.valueChanged.connect(self._on_volume)
        ctrl.addWidget(self.scale_volume, 1)
        sp.addSpacing(px(8))
        sp.addLayout(ctrl)
        self.lbl_titulo = self._rotulo("tituloMusica")
        self.lbl_artista = self._rotulo("artistaMusica")
        self.lbl_album = self._rotulo("albumMusica")
        self.lbl_sem_musica = self._rotulo("semMusica", t("no_spotify"))
        caixa_info = QVBoxLayout()
        caixa_info.setContentsMargins(0, 0, 0, 0)
        caixa_info.setSpacing(0)
        caixa_info.addWidget(self.lbl_titulo)
        caixa_info.addWidget(self.lbl_artista)
        caixa_info.addWidget(self.lbl_album)
        linha_musica = QHBoxLayout()
        linha_musica.setSpacing(px(10))
        linha_musica.addLayout(caixa_info, 1)
        self.espectro_area = _EspectroBarras(altura=px(55), largura=px(95))
        linha_musica.addWidget(self.espectro_area, 0, Qt.AlignmentFlag.AlignVCenter)
        sp.addLayout(linha_musica)
        sp.addWidget(self.lbl_sem_musica)
        col.addWidget(self._caixa_spotify)
        return pagina

    def _construir_previsao(self) -> QWidget:
        caixa = QWidget()
        linha = QHBoxLayout(caixa)
        linha.setContentsMargins(0, 0, 0, 0)
        linha.setSpacing(px(10))
        self._previsao_widgets = []
        for _ in range(3):
            col = QVBoxLayout()
            col.setSpacing(px(2))
            lbl_dia = self._rotulo("previsaoDia")
            img = QLabel()
            img.setFixedSize(px(20), px(20))
            lbl_temp = self._rotulo("previsaoTemp")
            col.addWidget(lbl_dia)
            col.addWidget(img)
            col.addWidget(lbl_temp)
            w = QWidget()
            w.setLayout(col)
            linha.addWidget(w, 1)
            self._previsao_widgets.append((lbl_dia, img, lbl_temp))
        return caixa

    def _painel_dir(self) -> QWidget:
        painel = QWidget()
        painel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        painel.setMinimumWidth(px(148))
        v = QVBoxLayout(painel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(px(6))
        v.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        linha = QHBoxLayout()
        linha.setSpacing(px(6))
        linha.setContentsMargins(0, 0, 0, 0)
        self.lbl_prog_dia = self._rotulo(
            "progLabel", t("day_progress"), Qt.AlignmentFlag.AlignRight)
        self.lbl_prog_pct = self._rotulo("progPct", "0%", Qt.AlignmentFlag.AlignRight)
        for w in (self.lbl_prog_dia, self.lbl_prog_pct):
            w.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        linha.addWidget(self.lbl_prog_dia)
        linha.addWidget(self.lbl_prog_pct)
        v.addLayout(linha)

        self.barra_dia = QProgressBar()
        self.barra_dia.setObjectName("barDia")
        self.barra_dia.setRange(0, 1000)
        self.barra_dia.setValue(0)
        self.barra_dia.setTextVisible(False)
        v.addWidget(self.barra_dia)

        self._cal_grid_host = QWidget()
        self._cal_grid = QGridLayout(self._cal_grid_host)
        self._cal_grid.setContentsMargins(0, px(4), 0, 0)
        self._cal_grid.setHorizontalSpacing(px(6))
        self._cal_grid.setVerticalSpacing(px(5))
        for col in range(7):
            self._cal_grid.setColumnStretch(col, 1)
            self._cal_grid.setColumnMinimumWidth(col, px(20))
        v.addWidget(self._cal_grid_host)
        self._painel_dir_w = painel
        self._atualizar_calendario()
        return painel

    def _aplicar_visibilidade(self):
        import config as cfg
        cal = bool(getattr(cfg, "MOSTRAR_CALENDARIO", True))
        self._cal_grid_host.setVisible(cal)
        self.lbl_prog_dia.setVisible(cal)
        self.lbl_prog_pct.setVisible(cal)
        self.barra_dia.setVisible(cal)
        self._painel_dir_w.setVisible(cal)
        self._caixa_spotify.setVisible(bool(getattr(cfg, "MOSTRAR_SPOTIFY", True)))
        self._caixa_previsao.setVisible(bool(getattr(cfg, "MOSTRAR_PREVISAO", True)))
        espectro_on = bool(getattr(cfg, "MOSTRAR_ESPECTRO", True))
        self.espectro_area.setVisible(espectro_on)
        if espectro_on:
            self._espectro.start()
        else:
            self._espectro.stop()
            self.espectro_area.set_levels([0.0] * N_BARS)

    def _largura_janela(self) -> int:
        # Qt precisa de mais largura que o GTK (calendário + “Progresso do dia”).
        return px(LARGURA) + px(120)

    def _ajustar_pagina(self):
        atual = self._stack.currentIndex()
        for i in range(self._stack.count()):
            pag = self._stack.widget(i)
            if i == atual:
                pag.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
                pag.setMaximumHeight(16777215)
            else:
                pag.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
                pag.setMaximumHeight(0)
        self.setFixedWidth(self._largura_janela())
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self._stack.adjustSize()
        self.adjustSize()

    def _toggle_config(self):
        if self._stack.currentIndex() == 1:
            self._stack.setCurrentIndex(0)
        else:
            self._pagina_cfg.carregar_valores()
            self._stack.setCurrentIndex(1)
        self._ajustar_pagina()

    def _apos_salvar(self):
        self.setStyleSheet(gerar_qss())
        self._atualizar_nota_spotify()
        self._atualizar_icone_clima(self._codigo_clima_atual)
        self._aplicar_visibilidade()
        self._ajustar_pagina()
        self._watch_mtimes = self._mtime_arquivos()
        try:
            import weather as mod_clima
            mod_clima.limpar_cache_clima()
        except Exception:
            pass
        self._buscar_clima()

    def _iniciar_timers(self):
        self._timer_relogio = QTimer(self)
        self._timer_relogio.timeout.connect(self._tick_relogio)
        self._timer_relogio.start(1000)
        self._timer_clima = QTimer(self)
        self._timer_clima.timeout.connect(self._buscar_clima)
        try:
            from config import ATUALIZAR_CLIMA_SEG
            ms = max(60, int(ATUALIZAR_CLIMA_SEG)) * 1000
        except Exception:
            ms = 600_000
        self._timer_clima.start(ms)
        self._timer_spotify = QTimer(self)
        self._timer_spotify.timeout.connect(self._tick_spotify)
        try:
            from config import ATUALIZAR_SPOTIFY_SEG
            sms = max(1, int(ATUALIZAR_SPOTIFY_SEG)) * 1000
        except Exception:
            sms = 3000
        self._timer_spotify.start(sms)
        QTimer.singleShot(400, self._tick_spotify)
        self._watch_mtimes = self._mtime_arquivos()
        self._timer_watch = QTimer(self)
        self._timer_watch.timeout.connect(self._verificar_arquivos)
        try:
            from config import VERIFICAR_ARQUIVOS_SEG
            wms = max(1, int(VERIFICAR_ARQUIVOS_SEG)) * 1000
        except Exception:
            wms = 5000
        self._timer_watch.start(wms)
        self._timer_espectro = QTimer(self)
        self._timer_espectro.timeout.connect(self._tick_espectro)
        self._timer_espectro.start(100)
        try:
            import wallpaper_theme as mod_wall
            self._wall_sig = mod_wall.assinatura_wallpaper()
        except Exception:
            self._wall_sig = None
        self._timer_wall = QTimer(self)
        self._timer_wall.timeout.connect(self._verificar_wallpaper)
        self._timer_wall.start(4000)

    def _arquivos_watch(self) -> list:
        arqs = []
        for pasta in (_RAIZ, _RAIZ / "config", _RAIZ / "win"):
            if not pasta.is_dir():
                continue
            for p in sorted(pasta.glob("*.py")):
                if not p.name.startswith("_"):
                    arqs.append(p)
        return arqs

    def _mtime_arquivos(self) -> dict:
        m = {}
        for p in self._arquivos_watch():
            try:
                m[p] = p.stat().st_mtime
            except OSError:
                pass
        return m

    @staticmethod
    def _arquivo_e_hot(p: Path) -> bool:
        return p.parent.name == "config" or p.name == "style.py"

    def _verificar_arquivos(self):
        atuais = self._mtime_arquivos()
        antigos = getattr(self, "_watch_mtimes", {})
        mudou_hot = False
        mudou_codigo = False
        for p, mt in atuais.items():
            if antigos.get(p) != mt:
                if self._arquivo_e_hot(p):
                    mudou_hot = True
                else:
                    mudou_codigo = True
        self._watch_mtimes = atuais
        if mudou_codigo:
            log.warning("código alterado — reiniciando o teste Qt")
            self._reiniciar_processo()
        elif mudou_hot:
            self._aplicar_hot_reload()

    def _aplicar_hot_reload(self):
        from win.settings import PaginaConfig
        PaginaConfig._recarregar_modulos()
        import win.settings as mod_set
        import win.window as mod_win
        from config.i18n import t as t_now
        mod_set.t = t_now
        mod_win.t = t_now
        self.setStyleSheet(gerar_qss())
        self._aplicar_visibilidade()
        if self._stack.currentIndex() != 1:
            self._pagina_cfg.carregar_valores()
        else:
            self._pagina_cfg._aplicar_idioma()
        self._tick_relogio()
        self.update()
        self.adjustSize()

    def _reiniciar_processo(self):
        import os
        import sys
        try:
            self._espectro.stop()
        except Exception:
            pass
        os.chdir(_RAIZ)
        os.execv(sys.executable, [sys.executable, str(_RAIZ / "main.py")])

    def _tick_espectro(self):
        import config as cfg
        if getattr(cfg, "MOSTRAR_ESPECTRO", True):
            self.espectro_area.set_levels(self._espectro.get_bars())

    def _verificar_wallpaper(self):
        import config as cfg
        if not getattr(cfg, "ADAPTAR_WALLPAPER_AUTO", False):
            return
        try:
            import wallpaper_theme as mod_wall
            sig = mod_wall.assinatura_wallpaper()
        except Exception:
            return
        antigo = self._wall_sig
        if antigo is None:
            self._wall_sig = sig
            return
        if sig == antigo:
            return
        self._wall_sig = sig
        caminho = sig[0] if sig else None
        anterior = antigo[0] if antigo else None
        if caminho and caminho != anterior:
            log.info("wallpaper mudou → %s", caminho)
            threading.Thread(target=self._bg_adaptar_wallpaper, daemon=True).start()
        elif caminho and sig[1] != (antigo[1] if len(antigo) > 1 else None):
            log.info("wallpaper atualizado → %s", caminho)
            threading.Thread(target=self._bg_adaptar_wallpaper, daemon=True).start()

    def _bg_adaptar_wallpaper(self):
        try:
            import wallpaper_theme as mod_wall
            tema, info = mod_wall.adaptar_ao_wallpaper()
        except Exception as e:
            log.debug("auto wallpaper: %s", e)
            return
        if tema:
            self.tema_wallpaper.emit(tema, info)

    def _aplicar_tema_wallpaper_auto(self, tema, info):
        if not tema:
            return
        try:
            from win.settings import _gravar_constantes
            cores = {
                k: v for k, v in tema.items()
                if str(k).startswith("COR_") or k == "OPACIDADE_FUNDO"
            }
            _gravar_constantes(_RAIZ / "config" / "colors.py", cores)
            self._aplicar_hot_reload()
            log.info("cores adaptadas automaticamente de %s", info)
        except Exception as e:
            log.warning("auto wallpaper: %s", e)

    def _atualizar_nota_spotify(self):
        from config import COR_DESTAQUE
        self.img_nota_spotify.setPixmap(pix_nota(px(16), COR_DESTAQUE))

    def _atualizar_icone_clima(self, codigo):
        from config import COR_TEXTO
        try:
            import weather as mod_clima
            tipo = mod_clima.SOL if codigo is None else mod_clima.tipo_icone(int(codigo))
        except Exception:
            tipo = "sol"
        self.img_icone_clima.setPixmap(pix_clima(tipo, px(36), COR_TEXTO))
        self._codigo_clima_atual = codigo

    def _tick_relogio(self):
        agora = datetime.datetime.now()
        self.lbl_hora.setText(agora.strftime("%H"))
        self.lbl_minuto.setText(agora.strftime("%M"))
        self.lbl_diasem.setText(t(f"weekday_{agora.weekday()}").upper())
        self.lbl_data.setText(
            f"{agora.day:02d} / {t(f'month_{agora.month}').upper()} / {agora.year}"
        )
        seg = agora.hour * 3600 + agora.minute * 60 + agora.second
        prog = seg / 86400
        self.lbl_prog_pct.setText(f"{int(prog * 100)}%")
        self.barra_dia.setValue(int(prog * 1000))
        if agora.day != self._cal_dia:
            self._cal_dia = agora.day
            self._atualizar_calendario()

    def _atualizar_calendario(self):
        while self._cal_grid.count():
            item = self._cal_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        agora = datetime.datetime.now()
        hoje = agora.day
        for col in range(7):
            lbl = self._rotulo("calHdr", t(f"cal_{col}"), Qt.AlignmentFlag.AlignHCenter)
            lbl.setMinimumWidth(px(20))
            self._cal_grid.addWidget(lbl, 0, col)
        for row, semana in enumerate(calendar.monthcalendar(agora.year, agora.month)):
            for col, dia in enumerate(semana):
                if dia == 0:
                    lbl = self._rotulo("calDia", "")
                else:
                    nome = "calHoje" if dia == hoje else "calDia"
                    lbl = self._rotulo(nome, str(dia), Qt.AlignmentFlag.AlignHCenter)
                lbl.setMinimumWidth(px(20))
                lbl.setMinimumHeight(px(16))
                self._cal_grid.addWidget(lbl, row + 1, col)
        self._cal_grid_host.updateGeometry()
        if getattr(self, "_painel_dir_w", None) is not None:
            self._painel_dir_w.updateGeometry()

    def _buscar_clima(self):
        threading.Thread(target=self._bg_clima, daemon=True).start()

    def _bg_clima(self):
        try:
            import weather as mod_clima
            dados = mod_clima.buscar()
        except Exception as e:
            log.warning("clima: %s", e)
            dados = None
        self.clima_pronto.emit(dados)

    def _aplicar_clima(self, dados):
        import config as cfg
        if not dados:
            self.lbl_cidade.setText(t("offline"))
            self.lbl_descricao.setText("")
            self.lbl_detalhe.setText("")
            return
        unidade_cfg = str(getattr(cfg, "UNIDADE_TEMPERATURA", "°C")).strip().upper()
        if unidade_cfg in ("°F", "F"):
            temp = dados.get("temp_f")
            if temp is None:
                temp = round(int(dados["temp"]) * 9 / 5 + 32)
            unidade = "°F"
        else:
            temp = dados.get("temp_c", dados["temp"])
            unidade = "°C"
        self._atualizar_icone_clima(dados.get("codigo"))
        self.lbl_temperatura.setText(f"{temp}{unidade}")
        self.lbl_cidade.setText(str(dados.get("cidade") or "--"))
        self.lbl_descricao.setText(str(dados.get("descricao") or ""))
        self.lbl_detalhe.setText(
            t("wind_hum", vento=dados.get("vento_ms", "--"),
              umidade=dados.get("umidade", "--"))
        )
        previsao = dados.get("previsao") or []
        from config import COR_TEXTO_SECUNDARIO
        import weather as mod_clima
        for i, (lbl_dia, img, lbl_temp) in enumerate(self._previsao_widgets):
            if i < len(previsao):
                d = previsao[i]
                lbl_dia.setText(str(d.get("dia", "")).upper())
                try:
                    tipo = mod_clima.tipo_icone(int(d.get("codigo", 113)))
                    img.setPixmap(pix_clima(tipo, px(20), COR_TEXTO_SECUNDARIO))
                except Exception:
                    img.clear()
                lbl_temp.setText(f"{d.get('max_c', '--')}° / {d.get('min_c', '--')}°")
            else:
                lbl_dia.setText("")
                img.clear()
                lbl_temp.setText("")
        if getattr(cfg, "NOTIFICAR_CHUVA_FORTE", True) and not dados.get("cache"):
            try:
                mod_clima.notificar_chuva_forte(dados)
            except Exception as e:
                log.debug("notificar chuva: %s", e)

    def _tick_spotify(self):
        if self._spotify_ocupado:
            return
        self._spotify_ocupado = True
        threading.Thread(target=self._bg_spotify, daemon=True).start()

    def _bg_spotify(self):
        try:
            import spotify as mod
            dados = mod.buscar_faixa()
        except Exception as e:
            log.debug("spotify: %s", e)
            dados = None
        self.spotify_pronto.emit(dados)

    def _aplicar_spotify(self, dados):
        self._spotify_ocupado = False
        ativo = bool(dados and dados.get("titulo"))
        for b in (self.btn_spotify_prev, self.btn_spotify_play, self.btn_spotify_next):
            b.setEnabled(ativo)
        self.scale_volume.setEnabled(ativo and dados.get("volume") is not None)
        if not ativo:
            self.lbl_sem_musica.show()
            self.lbl_titulo.hide()
            self.lbl_artista.hide()
            self.lbl_album.hide()
            self.lbl_cabecalho_spotify.setText(t("playing"))
            self.btn_capa.setIcon(QIcon())
            self._url_capa = None
            return
        self.lbl_sem_musica.hide()
        self.lbl_titulo.show()
        self.lbl_artista.show()
        self.lbl_album.show()
        tocando = str(dados.get("status") or "") == "Playing"
        self.lbl_cabecalho_spotify.setText(t("playing") if tocando else t("paused"))
        self.btn_spotify_play.setText("⏸" if tocando else "▶")
        self.btn_spotify_play.setToolTip(t("pause") if tocando else t("play"))
        titulo = str(dados.get("titulo") or "")
        if not tocando:
            try:
                from config import PREFIXO_PAUSADO
                titulo = f"{PREFIXO_PAUSADO}{titulo}"
            except Exception:
                pass
        self.lbl_titulo.setText(titulo)
        self.lbl_artista.setText(str(dados.get("artista") or ""))
        self.lbl_album.setText(str(dados.get("album") or ""))
        vol = dados.get("volume")
        if vol is not None and getattr(self, "_slider_ativo", None) is not self.scale_volume:
            self._volume_sync = True
            self.scale_volume.setValue(int(round(float(vol) * 100)))
            self._volume_sync = False
        capa = str(dados.get("capa") or "")
        capa_bytes = dados.get("capa_bytes")
        if capa and capa != self._url_capa:
            self._url_capa = capa
            if capa_bytes:
                self.capa_pronta.emit(capa_bytes)
            else:
                threading.Thread(target=self._bg_capa, args=(capa,), daemon=True).start()

    def _bg_capa(self, url: str):
        try:
            if url.startswith("file://"):
                dados = Path(url[7:]).read_bytes()
            else:
                import requests
                dados = requests.get(url, timeout=10).content
            self.capa_pronta.emit(dados)
        except Exception as e:
            log.debug("capa: %s", e)

    def _aplicar_capa(self, dados: bytes):
        pm = QPixmap()
        if not pm.loadFromData(dados):
            return
        lado = px(TAMANHO_CAPA)
        self.btn_capa.setIcon(QIcon(pm.scaled(
            lado, lado, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation)))
        self.btn_capa.setIconSize(self.btn_capa.size())

    def _spotify_cmd(self, metodo: str):
        threading.Thread(target=lambda: __import__("spotify").comando(metodo), daemon=True).start()
        QTimer.singleShot(300, self._tick_spotify)

    def _spotify_play_pause(self):
        metodo = "PlayPause"
        self._spotify_cmd(metodo)

    def _abrir_spotify(self):
        threading.Thread(target=lambda: __import__("spotify").abrir(), daemon=True).start()

    def _on_volume(self, valor: int):
        if self._volume_sync:
            return
        v = max(0.0, min(1.0, valor / 100.0))
        threading.Thread(
            target=lambda: __import__("spotify").definir_volume(v), daemon=True).start()

    def _geo_tela(self):
        screen = self.screen() or QApplication.primaryScreen()
        return screen.availableGeometry() if screen else None

    def _ligar_sinais_tela(self):
        if getattr(self, "_tela_sinais", False):
            return
        app = QApplication.instance()
        if app is None:
            return
        self._tela_sinais = True
        self._geo_conhecida = None
        app.screenAdded.connect(self._on_tela_mudou)
        app.screenRemoved.connect(self._on_tela_mudou)
        app.primaryScreenChanged.connect(self._on_tela_mudou)
        self._conectar_screen(self.screen() or app.primaryScreen())
        geo = self._geo_tela()
        if geo is not None:
            self._geo_conhecida = (geo.x(), geo.y(), geo.width(), geo.height())

    def _conectar_screen(self, screen):
        if screen is None:
            return
        antigo = getattr(self, "_screen_sinais", None)
        if antigo is screen:
            return
        if antigo is not None:
            for sig in (
                "availableGeometryChanged",
                "geometryChanged",
                "logicalDotsPerInchChanged",
            ):
                try:
                    getattr(antigo, sig).disconnect(self._on_tela_mudou)
                except Exception:
                    pass
        self._screen_sinais = screen
        screen.availableGeometryChanged.connect(self._on_tela_mudou)
        screen.geometryChanged.connect(self._on_tela_mudou)
        screen.logicalDotsPerInchChanged.connect(self._on_tela_mudou)

    def _on_tela_mudou(self, *args):
        QTimer.singleShot(250, self._reagir_mudanca_tela)

    def _reagir_mudanca_tela(self):
        if not self._janela_nativa:
            return
        self._conectar_screen(self.screen())
        geo = self._geo_tela()
        if geo is None:
            return
        atual = (geo.x(), geo.y(), geo.width(), geo.height())
        antigo = getattr(self, "_geo_conhecida", None)
        self._geo_conhecida = atual
        if antigo is None or antigo == atual:
            return
        log.info("tela mudou %s → %s", antigo, atual)
        self._pos_manual = False
        try:
            _POS_ARQ.unlink(missing_ok=True)
        except Exception:
            pass
        self._posicionar()
        aplicar_como_widget(self)

    def _posicionar(self):
        geo = self._geo_tela()
        if geo is None:
            return
        self.adjustSize()
        px_, py_ = self._carregar_posicao()
        if px_ < 0 or py_ < 0:
            px_, py_ = int(POS_X), int(POS_Y)
        if px_ >= 0 and py_ >= 0 and not self._posicao_visivel(px_, py_, geo):
            try:
                _POS_ARQ.unlink(missing_ok=True)
            except Exception:
                pass
            px_, py_ = -1, -1
        self._pos_manual = px_ >= 0 and py_ >= 0
        if self._pos_manual:
            x, y = self._clamp(px_, py_, geo)
        else:
            x = self._pos_x_lado(geo)
            y = geo.y() + (geo.height() - self.height()) // 2
        self.move(x, y)

    def _pos_x_lado(self, geo) -> int:
        if str(LADO).lower().startswith("esq"):
            return geo.x() + int(MARGEM_DIREITA)
        return geo.x() + geo.width() - self.width() - int(MARGEM_DIREITA)

    def _posicao_visivel(self, x: int, y: int, geo) -> bool:
        return (
            geo.x() - 40 <= x <= geo.x() + geo.width() - 40
            and geo.y() - 40 <= y <= geo.y() + geo.height() - 40
        )

    def _clamp(self, x: int, y: int, geo) -> tuple[int, int]:
        x = max(geo.x(), min(x, geo.x() + geo.width() - self.width()))
        y = max(geo.y(), min(y, geo.y() + geo.height() - self.height()))
        return x, y

    @staticmethod
    def _carregar_posicao() -> tuple[int, int]:
        try:
            a, b = _POS_ARQ.read_text(encoding="utf-8").split()
            return int(a), int(b)
        except Exception:
            return -1, -1

    def _salvar_posicao(self):
        try:
            _POS_ARQ.write_text(f"{self.x()} {self.y()}\n", encoding="utf-8")
        except Exception as e:
            log.debug("salvar posição: %s", e)

    def _resetar_posicao(self):
        try:
            _POS_ARQ.unlink(missing_ok=True)
        except Exception:
            pass
        self._pos_manual = False
        self._posicionar()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._menu_contexto(event.globalPosition().toPoint())
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            from PySide6.QtWidgets import QAbstractButton, QAbstractSlider, QLineEdit, QListWidget
            w = self.childAt(event.position().toPoint())
            while w is not None and w is not self:
                if isinstance(w, (QAbstractButton, QAbstractSlider, QLineEdit, QListWidget)):
                    super().mousePressEvent(event)
                    return
                w = w.parentWidget()
            self._arrastando = True
            self._drag_off = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._arrastando and event.buttons() & Qt.MouseButton.LeftButton:
            geo = self._geo_tela()
            pos = event.globalPosition().toPoint() - self._drag_off
            x, y = pos.x(), pos.y()
            if geo is not None:
                x, y = self._clamp(x, y, geo)
            self._pos_manual = True
            self.move(x, y)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._arrastando:
            self._arrastando = False
            self._salvar_posicao()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _menu_contexto(self, pos):
        menu = QMenu(self)
        act_v = QAction(t("version", v=VERSAO), self)
        act_v.setEnabled(False)
        menu.addAction(act_v)
        menu.addSeparator()
        menu.addAction(t("menu_settings"), self._toggle_config)
        menu.addAction(t("menu_reload_weather"), self._buscar_clima)
        menu.addAction(t("menu_reset_pos"), self._resetar_posicao)
        menu.addAction(t("menu_quit"), self._sair)
        menu.exec(pos)

    def _sair(self):
        try:
            self._espectro.stop()
        except Exception:
            pass
        QApplication.quit()

    def closeEvent(self, event):
        try:
            self._espectro.stop()
        except Exception:
            pass
        super().closeEvent(event)
