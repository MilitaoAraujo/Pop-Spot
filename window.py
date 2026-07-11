# Janela principal do widget — layout e loops de atualização
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GLib, Pango

import threading
import datetime
import calendar
import locale
import logging
import os
import sys
from pathlib import Path

from config import LARGURA, MARGEM_DIREITA, TAMANHO_CAPA
from config import ATUALIZAR_CLIMA_SEG, ATUALIZAR_SPOTIFY_SEG
from config import (
    ICONE_SPOTIFY, TEXTO_TOCANDO, TEXTO_PAUSADO, PREFIXO_PAUSADO, TEXTO_SEM_SPOTIFY,
    ICONE_SPOTIFY_ANTERIOR, ICONE_SPOTIFY_PROXIMO,
    ICONE_SPOTIFY_REPRODUZIR, ICONE_SPOTIFY_PAUSAR,
    TOOLTIP_SPOTIFY_ANTERIOR, TOOLTIP_SPOTIFY_PLAY, TOOLTIP_SPOTIFY_PAUSE, TOOLTIP_SPOTIFY_PROXIMO,
    ICONE_CLIMA_PADRAO, TEXTO_BUSCANDO_CLIMA, TEXTO_SEM_CONEXAO, FORMATO_VENTO_UMIDADE,
    UNIDADE_TEMPERATURA, DIAS_SEMANA, TEXTO_PROGRESSO_DIA,
)
from config import COR_DESTAQUE, COR_TEXTO, COR_BASE, COR_BOTOES_SPOTIFY, COR_SUPERFICIE
from css     import gerar_css
import weather  as mod_clima
import spotify  as mod_spotify
from spectrum import AudioSpectrum

log = logging.getLogger("widget")

import math as _math


def _hex_rgb(cor: str) -> tuple:
    """Converte #rrggbb ou rgba(...) → (r,g,b) no intervalo 0..1."""
    cor = cor.strip()
    if cor.startswith("#"):
        h = cor.lstrip("#")
        return int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255
    if cor.startswith("rgba"):
        p = cor[5:-1].split(",")
        return int(p[0])/255, int(p[1])/255, int(p[2])/255
    return 1.0, 1.0, 1.0


class _BotaoMedia(Gtk.DrawingArea):
    """Botão de controle desenhado com Cairo — ícone vetorial sem emoji ou tema GTK."""

    def __init__(self, tipo: str, tooltip: str):
        super().__init__()
        self._tipo       = tipo   # "prev" | "play" | "pause" | "next"
        self._habilitado = False
        self._hover      = False
        self._cor        = _hex_rgb(COR_BOTOES_SPOTIFY)
        self._cor_off    = (0.5, 0.5, 0.5)
        self._cor_bg     = _hex_rgb(COR_SUPERFICIE)

        self.set_size_request(52, 30)
        self.set_tooltip_text(tooltip)
        self.add_events(
            Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.connect("draw",               self._on_draw)
        self.connect("enter-notify-event", lambda *_: self._set_hover(True))
        self.connect("leave-notify-event", lambda *_: self._set_hover(False))

    def set_tipo(self, tipo: str):
        self._tipo = tipo
        self.queue_draw()

    def set_habilitado(self, v: bool):
        self._habilitado = v
        self.queue_draw()

    def _set_hover(self, v):
        self._hover = v
        self.queue_draw()

    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx, cy = w / 2, h / 2
        r_borda = 6

        # ── Fundo: transparente com leve camada escura ──────────────────
        try:
            import cairo
            cr.set_operator(cairo.OPERATOR_SOURCE)
        except ImportError:
            cr.set_operator(1)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        try:
            import cairo
            cr.set_operator(cairo.OPERATOR_OVER)
        except ImportError:
            cr.set_operator(2)

        # Fundo sólido com cantos arredondados (mesma cor de superfície do widget)
        cr.new_sub_path()
        cr.arc(r_borda,   r_borda,   r_borda, _math.pi,    3*_math.pi/2)
        cr.arc(w-r_borda, r_borda,   r_borda, -_math.pi/2, 0)
        cr.arc(w-r_borda, h-r_borda, r_borda, 0,           _math.pi/2)
        cr.arc(r_borda,   h-r_borda, r_borda, _math.pi/2,  _math.pi)
        cr.close_path()
        cr.set_source_rgb(*self._cor_bg)
        cr.fill_preserve()
        # Borda branca visível
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(1.2)
        cr.stroke()

        # ── Ícone ────────────────────────────────────────────────────────
        if not self._habilitado:
            cr.set_source_rgba(*self._cor_off, 0.30)
        elif self._hover:
            cr.set_source_rgba(*self._cor, 1.0)
        else:
            cr.set_source_rgba(*self._cor, 0.80)

        s = min(w, h) * 0.30
        self._draw_icon(cr, cx, cy, s)
        return True

    def _draw_icon(self, cr, cx, cy, s):
        if self._tipo == "play":
            cr.move_to(cx - s * 0.7, cy - s)
            cr.line_to(cx + s,       cy)
            cr.line_to(cx - s * 0.7, cy + s)
            cr.close_path()
            cr.fill()

        elif self._tipo == "pause":
            bw, g = s * 0.38, s * 0.28
            cr.rectangle(cx - g - bw, cy - s, bw, s * 2)
            cr.fill()
            cr.rectangle(cx + g,      cy - s, bw, s * 2)
            cr.fill()

        elif self._tipo in ("prev", "next"):
            d  = 1 if self._tipo == "next" else -1
            sep = s * 0.6
            for k in range(2):
                ox = d * sep * k
                if d > 0:
                    cr.move_to(cx + ox - s * 0.5, cy - s)
                    cr.line_to(cx + ox + s * 0.5, cy)
                    cr.line_to(cx + ox - s * 0.5, cy + s)
                else:
                    cr.move_to(cx + ox + s * 0.5,  cy - s)
                    cr.line_to(cx + ox - s * 0.5,  cy)
                    cr.line_to(cx + ox + s * 0.5,  cy + s)
                cr.close_path()
                cr.fill()

for _loc in ("pt_BR.UTF-8", "pt_BR", "pt_PT.UTF-8", "pt_PT", ""):
    try:
        locale.setlocale(locale.LC_TIME, _loc)
        break
    except locale.Error:
        continue


def _parsear_cores_espectro():
    def _hex(c):
        h = c.lstrip("#")
        return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return _hex(COR_BASE), _hex(COR_TEXTO), _hex(COR_DESTAQUE)


def _sessao_cosmic() -> bool:
    blob = (
        os.environ.get("XDG_CURRENT_DESKTOP", "")
        + " "
        + os.environ.get("XDG_SESSION_DESKTOP", "")
    ).upper()
    return "COSMIC" in blob


class WidgetDesktop(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._url_capa_atual  = None
        self._ls              = None
        self._pos_x           = 0
        self._pos_y           = 0
        self._spotify_ocupado = False
        self._altura_atual    = 800
        self._espectro        = AudioSpectrum()
        self._cal_dia         = -1
        self._cores_espectro  = _parsear_cores_espectro()
        self._hwnd_win32      = None   # handle Win32, usado no Windows

        _cfg = Path(__file__).parent / "config"
        self._config_arquivos = [p for p in _cfg.glob("*.py") if not p.name.startswith("_")]
        self._config_mtimes   = {p: p.stat().st_mtime for p in self._config_arquivos}

        self._aplicar_css()
        self._configurar_janela()
        self._construir_ui()
        self._iniciar_atualizacoes()
        self._espectro.start()

    # ── Configuração da janela ────────────────────────────────────────────

    def _aplicar_css(self):
        p = Gtk.CssProvider()
        p.load_from_data(gerar_css())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), p,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _configurar_janela(self):
        self.set_title("")
        self.set_decorated(False)
        self.set_resizable(False)

        tela   = self.get_screen()
        visual = tela.get_rgba_visual()
        if visual and tela.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.connect("draw", self._desenhar_fundo)
        self.connect_after("realize", self._ao_realizar)

        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geo     = monitor.get_geometry()
        self._monitor_geo = geo
        self._pos_x = geo.x + geo.width - LARGURA - MARGEM_DIREITA
        self._pos_y = geo.y + (geo.height - self._altura_atual) // 2

        if self._ativar_layer_shell():
            log.info("gtk-layer-shell ativo (Wayland)")
        else:
            self.set_keep_below(True)
            self.set_skip_taskbar_hint(True)
            self.set_skip_pager_hint(True)
            self.stick()
            self.move(self._pos_x, self._pos_y)

    def _ao_realizar(self, *_args):
        GLib.idle_add(self._aplicar_input_shape)
        if sys.platform == "win32":
            # Aguarda 800ms para garantir que a janela está completamente visível
            GLib.timeout_add(800, self._ocultar_taskbar_windows)
            self.connect("focus-in-event", self._on_foco_win32)

    def _ocultar_taskbar_windows(self):
        """Remove o widget da taskbar/Alt+Tab e o mantém abaixo de todas as
        janelas via Win32 API.  Chamado uma vez após realize; o timer
        _manter_abaixo_win32 reforça o keep-below a cada 500 ms."""
        try:
            import ctypes
            import ctypes.wintypes
            import os as _os

            GWL_EXSTYLE      = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW  = 0x00040000

            hwnd = None

            # Tentativa 1: via GdkWin32
            gdk_win = self.get_window()
            if gdk_win:
                try:
                    gi.require_version("GdkWin32", "3.0")
                    from gi.repository import GdkWin32
                    hwnd = GdkWin32.Win32Window.get_handle(gdk_win)
                except Exception:
                    pass

            # Tentativa 2: enumera janelas visíveis do nosso processo
            if not hwnd:
                pid   = _os.getpid()
                found = []
                CBTYPE = ctypes.WINFUNCTYPE(
                    ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
                def _cb(h, _):
                    d = ctypes.wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(h, ctypes.byref(d))
                    if d.value == pid and ctypes.windll.user32.IsWindowVisible(h):
                        found.append(h)
                    return True
                ctypes.windll.user32.EnumWindows(CBTYPE(_cb), 0)
                if found:
                    hwnd = found[0]

            if not hwnd:
                return False

            self._hwnd_win32 = hwnd

            # Aplica estilos Win32:
            #   WS_EX_TOOLWINDOW  → sem taskbar / Alt+Tab
            #   WS_EX_NOACTIVATE  → cliques não ativam a janela (evita escurecer)
            GWL_EXSTYLE        = -20
            WS_EX_TOOLWINDOW   = 0x00000080
            WS_EX_APPWINDOW    = 0x00040000
            WS_EX_NOACTIVATE   = 0x08000000
            SWP_NOMOVE         = 0x0002
            SWP_NOSIZE         = 0x0001
            SWP_NOZORDER       = 0x0004
            SWP_FRAMECHANGED   = 0x0020

            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE) & ~WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            ctypes.windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )

            # Posiciona atrás de todas as janelas (desktop widget)
            self._manter_abaixo_win32()

            log.debug("Win32: TOOLWINDOW + FRAMECHANGED + HWND_BOTTOM (hwnd=%s)", hwnd)
        except Exception as e:
            log.debug("ocultar_taskbar_windows: %s", e)
        return False

    def _manter_abaixo_win32(self):
        """Empurra o widget para trás de todas as janelas (HWND_BOTTOM)."""
        if not self._hwnd_win32:
            return False
        try:
            import ctypes
            HWND_BOTTOM    = 1
            SWP_NOMOVE     = 0x0002
            SWP_NOSIZE     = 0x0001
            SWP_NOACTIVATE = 0x0010
            ctypes.windll.user32.SetWindowPos(
                self._hwnd_win32, HWND_BOTTOM, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
        except Exception as e:
            log.debug("manter_abaixo_win32: %s", e)
        return False

    def _on_foco_win32(self, *_args):
        """Quando o widget recebe foco acidentalmente, volta para o fundo."""
        GLib.idle_add(self._manter_abaixo_win32)
        return False

    def _aplicar_input_shape(self):
        if not self._ls:
            return False
        gw = self.get_window()
        if gw:
            try:
                gw.merge_child_input_shapes()
            except Exception as e:
                log.debug("input shape: %s", e)
        return False

    def _desenhar_fundo(self, _widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        try:
            import cairo
            cr.set_operator(cairo.OPERATOR_SOURCE)
        except ImportError:
            cr.set_operator(1)
        cr.paint()
        return False

    def _ativar_layer_shell(self):
        try:
            gi.require_version("GtkLayerShell", "0.1")
            from gi.repository import GtkLayerShell

            self._ls = GtkLayerShell
            GtkLayerShell.init_for_window(self)
            if hasattr(GtkLayerShell, "set_namespace"):
                GtkLayerShell.set_namespace(self, "desktop-widget")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP,  True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP,  max(0, self._pos_y))
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, max(0, self._pos_x))
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
            if hasattr(GtkLayerShell, "set_exclusive_zone"):
                GtkLayerShell.set_exclusive_zone(self, 0)
            return True
        except Exception:
            self._ls = None
            return False

    def _inicializar_altura(self, _widget):
        GLib.idle_add(self._medir_altura_natural)

    def _medir_altura_natural(self):
        _min, nat = self._raiz.get_preferred_height()
        h = nat + 20
        self._altura_atual = h
        self._raiz.set_size_request(LARGURA, nat)
        geo = self._monitor_geo
        self._pos_y = geo.y + (geo.height - h) // 2
        self._mover_para(self._pos_x, self._pos_y)
        self.queue_resize()
        GLib.idle_add(self._aplicar_input_shape)
        return False

    # ── Altura exata para o Wayland ───────────────────────────────────────

    def do_get_preferred_height(self):
        if self._altura_atual > 0:
            h = self._altura_atual
            return (h, h)
        return Gtk.Window.do_get_preferred_height(self)

    def do_get_preferred_height_for_width(self, width):
        if self._altura_atual > 0:
            h = self._altura_atual
            return (h, h)
        return Gtk.Window.do_get_preferred_height_for_width(self, width)

    def _mover_para(self, x, y):
        self._pos_x = x
        self._pos_y = y
        if self._ls:
            self._ls.set_margin(self, self._ls.Edge.LEFT, max(0, x))
            self._ls.set_margin(self, self._ls.Edge.TOP,  max(0, y))
            self.queue_resize()
        else:
            self.move(x, y)

    # ── Construção da interface ───────────────────────────────────────────

    def _construir_ui(self):
        raiz = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        raiz.get_style_context().add_class("raiz")
        raiz.set_size_request(LARGURA, -1)
        self._raiz = raiz

        # Relógio
        self.lbl_hora    = self._rotulo("hora",         "00", Gtk.Align.START)
        self.lbl_minuto  = self._rotulo("minuto",       "00", Gtk.Align.START)
        self.lbl_diasem  = self._rotulo("diaSemana",    "",   Gtk.Align.START)
        self.lbl_data    = self._rotulo("dataCompleta", "",   Gtk.Align.START)

        caixa_clock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for w in (self.lbl_hora, self.lbl_minuto, self.lbl_diasem, self.lbl_data):
            caixa_clock.pack_start(w, False, False, 0)

        caixa_relogio = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        caixa_relogio.pack_start(caixa_clock,                  True,  True,  0)
        caixa_relogio.pack_start(self._construir_painel_dir(), False, False, 0)
        raiz.pack_start(caixa_relogio, False, False, 0)

        raiz.pack_start(self._separador(), False, False, 0)

        # Clima
        caixa_clima = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        linha_temp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.lbl_icone_clima = self._rotulo("iconeClima",       ICONE_CLIMA_PADRAO, Gtk.Align.START)
        self.lbl_temperatura = self._rotulo("temperaturaClima", "--°C",             Gtk.Align.START)
        linha_temp.pack_start(self.lbl_icone_clima, False, False, 0)
        linha_temp.pack_start(self.lbl_temperatura, False, False, 0)
        caixa_clima.pack_start(linha_temp, False, False, 0)

        self.lbl_cidade    = self._rotulo("cidadeClima",    "--",               Gtk.Align.START)
        self.lbl_descricao = self._rotulo("descricaoClima", TEXTO_BUSCANDO_CLIMA, Gtk.Align.START)
        self.lbl_detalhe   = self._rotulo("detalheClima",   "",                 Gtk.Align.START)
        for w in (self.lbl_cidade, self.lbl_descricao, self.lbl_detalhe):
            caixa_clima.pack_start(w, False, False, 0)

        raiz.pack_start(caixa_clima, False, False, 0)
        raiz.pack_start(self._separador(), False, False, 0)

        # Spotify
        caixa_spotify = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        linha_cabecalho = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        linha_cabecalho.pack_start(
            self._rotulo("cabecalhoSpotify", ICONE_SPOTIFY, Gtk.Align.START), False, False, 0)
        self.lbl_cabecalho_spotify = self._rotulo("cabecalhoSpotify", TEXTO_TOCANDO, Gtk.Align.START)
        linha_cabecalho.pack_start(self.lbl_cabecalho_spotify, False, False, 0)
        caixa_spotify.pack_start(linha_cabecalho, False, False, 0)

        envoltorio_capa = Gtk.Box()
        envoltorio_capa.set_halign(Gtk.Align.START)
        self.img_capa = Gtk.Image()
        self.img_capa.set_size_request(TAMANHO_CAPA, TAMANHO_CAPA)
        envoltorio_capa.pack_start(self.img_capa, False, False, 0)
        caixa_spotify.pack_start(envoltorio_capa, False, False, 8)

        linha_ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        linha_ctrl.set_halign(Gtk.Align.START)
        self.btn_spotify_prev = _BotaoMedia("prev", TOOLTIP_SPOTIFY_ANTERIOR)
        self.btn_spotify_prev.connect("button-release-event", self._on_spotify_prev)
        self.btn_spotify_play = _BotaoMedia("play", TOOLTIP_SPOTIFY_PLAY)
        self.btn_spotify_play.connect("button-release-event", self._on_spotify_play_pause)
        self.btn_spotify_next = _BotaoMedia("next", TOOLTIP_SPOTIFY_PROXIMO)
        self.btn_spotify_next.connect("button-release-event", self._on_spotify_next)
        for b in (self.btn_spotify_prev, self.btn_spotify_play, self.btn_spotify_next):
            linha_ctrl.pack_start(b, False, False, 0)
        caixa_spotify.pack_start(linha_ctrl, False, False, 8)

        self.lbl_titulo     = self._rotulo("tituloMusica",  "", Gtk.Align.START, reticencias=True)
        self.lbl_artista    = self._rotulo("artistaMusica", "", Gtk.Align.START, reticencias=True)
        self.lbl_album      = self._rotulo("albumMusica",   "", Gtk.Align.START, reticencias=True)
        self.lbl_sem_musica = self._rotulo("semMusica", TEXTO_SEM_SPOTIFY, Gtk.Align.START)

        caixa_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for w in (self.lbl_titulo, self.lbl_artista, self.lbl_album):
            caixa_info.pack_start(w, False, False, 0)

        self.espectro_area = Gtk.DrawingArea()
        self.espectro_area.set_size_request(95, 55)
        self.espectro_area.set_valign(Gtk.Align.CENTER)
        self.espectro_area.connect("draw", self._desenhar_espectro)

        linha_musica = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        linha_musica.pack_start(caixa_info,         True,  True,  0)
        linha_musica.pack_start(self.espectro_area, False, False, 0)

        caixa_spotify.pack_start(linha_musica,       False, False, 0)
        caixa_spotify.pack_start(self.lbl_sem_musica, False, False, 0)

        raiz.pack_start(caixa_spotify, False, False, 0)

        self.connect("map", self._inicializar_altura)
        self.connect_after("map", self._pulso_superficie_wayland)
        self.connect("button-press-event", self._iniciar_arrasto)
        self.add(raiz)

    # ── Painel direito do relógio (progresso + calendário) ────────────────

    def _construir_painel_dir(self):
        painel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        painel.set_valign(Gtk.Align.CENTER)
        painel.set_size_request(95, -1)

        linha_prog = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        linha_prog.set_halign(Gtk.Align.END)
        if TEXTO_PROGRESSO_DIA:
            linha_prog.pack_start(
                self._rotulo("progLabel", TEXTO_PROGRESSO_DIA, Gtk.Align.END), False, False, 0)
        self.lbl_prog_pct = self._rotulo("progPct", "0%", Gtk.Align.END)
        linha_prog.pack_start(self.lbl_prog_pct, False, False, 0)
        painel.pack_start(linha_prog, False, False, 0)

        self.barra_dia = Gtk.ProgressBar()
        self.barra_dia.get_style_context().add_class("barDia")
        self.barra_dia.set_show_text(False)
        self.barra_dia.set_fraction(0.0)
        painel.pack_start(self.barra_dia, False, False, 0)

        self._cal_grid = Gtk.Grid()
        self._cal_grid.set_column_spacing(4)
        self._cal_grid.set_row_spacing(3)
        self._cal_grid.set_halign(Gtk.Align.END)
        painel.pack_start(self._cal_grid, False, False, 10)

        return painel

    def _atualizar_calendario(self):
        for child in list(self._cal_grid.get_children()):
            self._cal_grid.remove(child)

        agora = datetime.datetime.now()
        hoje  = agora.day

        for col, h in enumerate(DIAS_SEMANA):
            lbl = Gtk.Label(label=h)
            lbl.get_style_context().add_class("calHdr")
            self._cal_grid.attach(lbl, col, 0, 1, 1)

        for row, semana in enumerate(calendar.monthcalendar(agora.year, agora.month)):
            for col, dia in enumerate(semana):
                if dia == 0:
                    lbl = Gtk.Label(label="")
                else:
                    lbl = Gtk.Label(label=str(dia))
                    lbl.get_style_context().add_class("calHoje" if dia == hoje else "calDia")
                self._cal_grid.attach(lbl, col, row + 1, 1, 1)

        self._cal_grid.show_all()

    # ── Helpers de UI ─────────────────────────────────────────────────────

    def _rotulo(self, classe_css, texto="", halign=Gtk.Align.START, reticencias=False):
        lbl = Gtk.Label(label=texto)
        lbl.get_style_context().add_class(classe_css)
        lbl.set_halign(halign)
        if reticencias:
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            lbl.set_max_width_chars(30)
        return lbl



    def _separador(self):
        s = Gtk.EventBox()
        s.get_style_context().add_class("sep")
        s.set_hexpand(True)
        return s

    def _iniciar_arrasto(self, widget, event):
        """Permite mover o widget clicando e arrastando em qualquer área que
        não seja um botão interativo."""
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            alvo = Gtk.get_event_widget(event)
            if alvo and not isinstance(alvo, (Gtk.Button, _BotaoMedia)):
                self.begin_move_drag(1, int(event.x_root), int(event.y_root), event.time)
                return True
        return False

    def _pulso_superficie_wayland(self, *_args):
        if not self._ls:
            return
        GLib.idle_add(self._pulso_frame)
        GLib.timeout_add(400, self._pulso_frame)
        if _sessao_cosmic():
            for ms in (900, 2200, 3000, 8000):
                GLib.timeout_add(ms, self._pulso_frame)

    def _pulso_frame(self):
        gw = self.get_window()
        if gw:
            try:
                gw.invalidate_rect(None, True)
            except Exception:
                pass
        self.queue_resize()
        self._aplicar_input_shape()
        return False

    # ── Visualizador de espectro ──────────────────────────────────────────

    def _desenhar_espectro(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        if w == 0 or h == 0:
            return False

        bars = self._espectro.get_bars()
        n    = len(bars)
        cor_base, cor_texto, cor_destaque = self._cores_espectro
        silencio = all(v < 0.03 for v in bars)
        base = h - 0.75

        if silencio or n == 0:
            cr.set_source_rgba(*cor_texto, 0.20)
            cr.set_line_width(1.5)
            cr.move_to(0, base)
            cr.line_to(w, base)
            cr.stroke()
            return False

        gap   = 2
        bar_w = max(1.0, (w - gap * (n - 1)) / n)

        for i, val in enumerate(bars):
            bar_h = max(1.5, val * h)
            x     = i * (bar_w + gap)
            y     = h - bar_h

            if val < 0.45:
                t = val / 0.45
                r = cor_base[0] + (cor_texto[0] - cor_base[0]) * t
                g = cor_base[1] + (cor_texto[1] - cor_base[1]) * t
                b = cor_base[2] + (cor_texto[2] - cor_base[2]) * t
                a = 0.30 + t * 0.35
            else:
                t = (val - 0.45) / 0.55
                r = cor_texto[0] + (cor_destaque[0] - cor_texto[0]) * t
                g = cor_texto[1] + (cor_destaque[1] - cor_texto[1]) * t
                b = cor_texto[2] + (cor_destaque[2] - cor_texto[2]) * t
                a = 0.65 + t * 0.35

            cr.set_source_rgba(r, g, b, a)
            cr.rectangle(x, y, bar_w, bar_h)
            cr.fill()

        return False

    def _tick_espectro(self):
        if self.espectro_area.get_visible():
            self.espectro_area.queue_draw()
        return True

    # ── Loop de atualização ───────────────────────────────────────────────

    def _iniciar_atualizacoes(self):
        self._tick_relogio()
        GLib.timeout_add_seconds(1, self._tick_relogio)

        threading.Thread(target=self._bg_clima, daemon=True).start()
        GLib.timeout_add_seconds(
            ATUALIZAR_CLIMA_SEG,
            lambda: threading.Thread(target=self._bg_clima, daemon=True).start() or True,
        )

        self._tick_spotify()
        GLib.timeout_add_seconds(ATUALIZAR_SPOTIFY_SEG, self._tick_spotify)
        GLib.timeout_add(67, self._tick_espectro)
        GLib.timeout_add(1500, self._verificar_config)

    # ── Hot reload ───────────────────────────────────────────────────────

    def _verificar_config(self):
        if any(p.stat().st_mtime != self._config_mtimes[p] for p in self._config_arquivos):
            log.warning("Configuração alterada — reiniciando")
            self._espectro.stop()
            if sys.platform == "win32":
                import subprocess
                subprocess.Popen([sys.executable] + sys.argv)
                Gtk.main_quit()
            else:
                os.execv(sys.executable, [sys.executable] + sys.argv)
        return True

    # ── Relógio ───────────────────────────────────────────────────────────

    def _tick_relogio(self):
        agora = datetime.datetime.now()
        self.lbl_hora.set_text(agora.strftime("%H"))
        self.lbl_minuto.set_text(agora.strftime("%M"))
        self.lbl_diasem.set_text(agora.strftime("%A").upper())
        self.lbl_data.set_text(agora.strftime("%d / %B / %Y").upper())

        seg  = agora.hour * 3600 + agora.minute * 60 + agora.second
        prog = seg / 86400
        self.lbl_prog_pct.set_text(f"{int(prog * 100)}%")
        self.barra_dia.set_fraction(prog)

        if agora.day != self._cal_dia:
            self._cal_dia = agora.day
            self._atualizar_calendario()

        return True

    # ── Clima ─────────────────────────────────────────────────────────────

    def _bg_clima(self):
        dados = mod_clima.buscar()
        GLib.idle_add(self._aplicar_clima, dados)

    def _aplicar_clima(self, dados):
        if dados:
            self.lbl_icone_clima.set_text(mod_clima.icone(dados["codigo"]))
            self.lbl_temperatura.set_text(f"  {dados['temp']}{UNIDADE_TEMPERATURA}")
            self.lbl_cidade.set_text(dados["cidade"])
            self.lbl_descricao.set_text(dados["descricao"])
            self.lbl_detalhe.set_text(
                FORMATO_VENTO_UMIDADE.format(vento=dados["vento_ms"], umidade=dados["umidade"])
            )
        else:
            self.lbl_cidade.set_text(TEXTO_SEM_CONEXAO)
            self.lbl_descricao.set_text("")
            self.lbl_detalhe.set_text("")
        return False

    # ── Spotify ───────────────────────────────────────────────────────────

    def _tick_spotify(self):
        if self._spotify_ocupado:
            return True
        self._spotify_ocupado = True
        threading.Thread(target=self._bg_spotify, daemon=True).start()
        return True

    def _bg_spotify(self):
        try:
            dados = mod_spotify.buscar_faixa()
            GLib.idle_add(self._aplicar_spotify, dados)
        finally:
            self._spotify_ocupado = False

    def _spotify_refresh_once(self):
        self._tick_spotify()
        return False

    def _on_spotify_prev(self, _widget, event):
        if event.button == 1 and mod_spotify.comando("Previous"):
            GLib.timeout_add(200, self._spotify_refresh_once)

    def _on_spotify_next(self, _widget, event):
        if event.button == 1 and mod_spotify.comando("Next"):
            GLib.timeout_add(200, self._spotify_refresh_once)

    def _on_spotify_play_pause(self, _widget, event):
        if event.button == 1 and mod_spotify.comando("PlayPause"):
            GLib.timeout_add(200, self._spotify_refresh_once)

    def _aplicar_spotify(self, dados):
        tocando = dados and dados["status"] in ("Playing", "Running")
        pausado = dados and dados["status"] == "Paused"

        spotify_aberto = bool(dados)
        for b in (self.btn_spotify_prev, self.btn_spotify_play, self.btn_spotify_next):
            b.set_habilitado(spotify_aberto)
        if dados:
            self.btn_spotify_play.set_tipo("pause" if tocando else "play")
            self.btn_spotify_play.set_tooltip_text(
                TOOLTIP_SPOTIFY_PAUSE if tocando else TOOLTIP_SPOTIFY_PLAY)

        self.lbl_sem_musica.set_visible(not spotify_aberto)
        if dados:
            fonte = dados.get("fonte", "Spotify")
            if pausado:
                cabecalho = TEXTO_PAUSADO
            elif fonte == "Spotify":
                cabecalho = TEXTO_TOCANDO
            else:
                cabecalho = fonte.upper()
            self.lbl_cabecalho_spotify.set_text(cabecalho)
        else:
            self.lbl_cabecalho_spotify.set_text("")

        if tocando or pausado:
            prefixo = PREFIXO_PAUSADO if pausado else ""
            self.lbl_titulo.set_text(prefixo + dados["titulo"])
            self.lbl_artista.set_text(dados["artista"])
            self.lbl_album.set_text(dados["album"])
            capa = dados["capa"]
            if capa and capa != self._url_capa_atual:
                self._url_capa_atual = capa
                threading.Thread(target=self._bg_capa, args=(capa,), daemon=True).start()
        # Quando Spotify está fechado (dados is None), mantém capa e textos da
        # última música — não limpa nada, o usuário vê a última faixa ouvida.
        return False

    def _bg_capa(self, url):
        pb = mod_spotify.carregar_capa(url, TAMANHO_CAPA)
        GLib.idle_add(self._aplicar_capa, pb)

    def _aplicar_capa(self, pb):
        if pb:
            self.img_capa.set_from_pixbuf(pb)
        return False
