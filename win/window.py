"""Janela Qt do Pop Spot — clone visual do widget GTK (página principal)."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import (
    COR_BASE,
    LADO,
    LARGURA,
    MARGEM_DIREITA,
    OPACIDADE_FUNDO,
    POS_X,
    POS_Y,
    RAIO_BORDA,
    VERSAO,
)
from config.i18n import t
from plugins.clima_qt import ClimaPlugin
from plugins.espectro_qt import EspectroPlugin
from plugins.midia_qt import MidiaPlugin
from plugins.relogio_qt import RelogioPlugin
from win.native import aplicar_como_widget, permitir_foco
from win.scale import px
from win.settings import PaginaConfig
from win.style import gerar_qss

log = logging.getLogger("popspot.win")

_RAIZ = Path(__file__).resolve().parent.parent
_POS_ARQ = _RAIZ / "config" / ".widget_pos"


class _Painel(QWidget):
    """Fundo arredondado com a cor/opacidade do tema."""

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cor = QColor(COR_BASE)
        cor.setAlphaF(max(0.0, min(1.0, float(OPACIDADE_FUNDO))))
        p.setBrush(cor)
        p.setPen(Qt.PenStyle.NoPen)
        r = px(RAIO_BORDA)
        p.drawRoundedRect(self.rect(), r, r)


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
        self._slider_ativo = None
        self._previsao_widgets: list[tuple[QLabel, QLabel, QLabel]] = []
        self._plugin_espectro = EspectroPlugin()
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

        self._plugin_relogio = RelogioPlugin()
        relogio_widget = self._plugin_relogio.montar(self)
        self.lbl_hora = self._plugin_relogio.lbl_hora
        self.lbl_minuto = self._plugin_relogio.lbl_minuto
        self.lbl_diasem = self._plugin_relogio.lbl_diasem
        self.lbl_data = self._plugin_relogio.lbl_data
        self.lbl_prog_dia = self._plugin_relogio.lbl_prog_dia
        self.lbl_prog_pct = self._plugin_relogio.lbl_prog_pct
        self.barra_dia = self._plugin_relogio.barra_dia
        self._cal_grid_host = self._plugin_relogio.cal_grid_host
        self._cal_grid = self._plugin_relogio.cal_grid
        self._painel_dir_w = self._plugin_relogio.painel_dir_w
        col.addWidget(relogio_widget)
        col.addWidget(self._sep())

        self._plugin_clima = ClimaPlugin()
        clima_widget = self._plugin_clima.montar(self)
        self.img_icone_clima = self._plugin_clima.img_icone
        self.lbl_temperatura = self._plugin_clima.lbl_temperatura
        self.lbl_cidade = self._plugin_clima.lbl_cidade
        self.lbl_descricao = self._plugin_clima.lbl_descricao
        self.lbl_detalhe = self._plugin_clima.lbl_detalhe
        self._previsao_widgets = self._plugin_clima.previsao_widgets
        self._caixa_previsao = self._plugin_clima.caixa_previsao
        col.addWidget(clima_widget)
        col.addWidget(self._sep())

        self.espectro_area = self._plugin_espectro.montar(self)
        self._plugin_midia = MidiaPlugin()
        self._caixa_spotify = self._plugin_midia.montar(self)
        self.lbl_cabecalho_spotify = self._plugin_midia.lbl_cabecalho
        self.img_nota_spotify = self._plugin_midia.img_nota
        self.btn_capa = self._plugin_midia.btn_capa
        self.btn_spotify_prev = self._plugin_midia.btn_prev
        self.btn_spotify_play = self._plugin_midia.btn_play
        self.btn_spotify_next = self._plugin_midia.btn_next
        self.scale_volume = self._plugin_midia.scale_volume
        self.lbl_titulo = self._plugin_midia.lbl_titulo
        self.lbl_artista = self._plugin_midia.lbl_artista
        self.lbl_album = self._plugin_midia.lbl_album
        self.lbl_sem_musica = self._plugin_midia.lbl_sem_musica
        self.img_status_musica = self._plugin_midia.img_status
        col.addWidget(self._caixa_spotify)
        return pagina

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
        self._plugin_espectro.aplicar_visibilidade()

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
            self._permitir_digitar(False)
        else:
            self._pagina_cfg.carregar_valores()
            self._stack.setCurrentIndex(1)
            self._permitir_digitar(True)
        self._ajustar_pagina()

    def _permitir_digitar(self, aceitar: bool) -> None:
        """Liga/desliga o foco de teclado da janela.

        Por padrão a janela não aceita foco pra nunca roubar do app ativo
        (WindowDoesNotAcceptFocus + WS_EX_NOACTIVATE no Windows) — mas isso
        também bloqueia campos de texto. O Qt guarda esse estado na própria
        flag da janela (não só no estilo nativo do Windows), então mudar só o
        bit do Windows não basta: precisa trocar a flag do Qt e remostrar.
        """
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, not aceitar)
        if self._janela_nativa:
            self.show()
        permitir_foco(self, aceitar)

    def _apos_salvar(self):
        self.setStyleSheet(gerar_qss())
        self._repintar_icones_tema()
        self._aplicar_visibilidade()
        self._ajustar_pagina()
        self.update()
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
        import plugins.clima_qt as mod_clima_plugin
        import plugins.midia_qt as mod_midia_plugin
        import plugins.relogio_qt as mod_relogio
        import win.settings as mod_set
        import win.window as mod_win
        from config.i18n import t as t_now

        mod_set.t = t_now
        mod_win.t = t_now
        mod_relogio.t = t_now
        mod_clima_plugin.t = t_now
        mod_midia_plugin.t = t_now
        self.setStyleSheet(gerar_qss())
        self._repintar_icones_tema()
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
            self._plugin_espectro.parar()
        except Exception:
            pass
        os.chdir(_RAIZ)
        os.execv(sys.executable, [sys.executable, str(_RAIZ / "main.py")])

    def _tick_espectro(self):
        self._plugin_espectro.tick()

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

            cores = {k: v for k, v in tema.items() if str(k).startswith("COR_") or k == "OPACIDADE_FUNDO"}
            _gravar_constantes(_RAIZ / "config" / "colors.py", cores)
            self._aplicar_hot_reload()
            log.info("cores adaptadas automaticamente de %s", info)
        except Exception as e:
            log.warning("auto wallpaper: %s", e)

    def _tick_relogio(self):
        self._plugin_relogio.on_update()

    def _buscar_clima(self):
        threading.Thread(target=self._bg_clima, daemon=True).start()

    def _bg_clima(self):
        self._plugin_clima.buscar()

    def _aplicar_clima(self, dados):
        self._plugin_clima.aplicar(dados)

    def _tick_spotify(self):
        self._plugin_midia.tick()

    def _aplicar_spotify(self, dados):
        self._plugin_midia.aplicar(dados)

    def _aplicar_capa(self, dados: bytes):
        self._plugin_midia.aplicar_capa(dados)

    def _repintar_icones_tema(self):
        """Redesenha os ícones que têm a cor gravada num QPixmap (não seguem
        QSS sozinhos), pra reagir na hora a uma troca de tema/cor."""
        self._plugin_midia.on_theme_change(None)
        self._plugin_clima.on_theme_change(None)

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
            self._plugin_espectro.parar()
        except Exception:
            pass
        QApplication.quit()

    def closeEvent(self, event):
        try:
            self._plugin_espectro.parar()
        except Exception:
            pass
        super().closeEvent(event)
        # setQuitOnLastWindowClosed está desligado (ver win/main.py), então um
        # fechamento real da janela principal (ex.: logoff do Windows) precisa
        # encerrar o app explicitamente, senão ele vira um processo invisível.
        QApplication.quit()
