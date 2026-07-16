# Janela principal do widget — layout, config viva e loops de atualização
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
import re
from pathlib import Path

from config import (
    LARGURA, MARGEM_DIREITA, TAMANHO_CAPA, LADO, POS_X, POS_Y, ESCALA,
    ATUALIZAR_CLIMA_SEG, ATUALIZAR_SPOTIFY_SEG,
    TEXTO_TOCANDO, TEXTO_PAUSADO, PREFIXO_PAUSADO, TEXTO_SEM_SPOTIFY,
    ICONE_SPOTIFY_ANTERIOR, ICONE_SPOTIFY_PROXIMO,
    ICONE_SPOTIFY_REPRODUZIR, ICONE_SPOTIFY_PAUSAR,
    TOOLTIP_SPOTIFY_ANTERIOR, TOOLTIP_SPOTIFY_PLAY, TOOLTIP_SPOTIFY_PAUSE, TOOLTIP_SPOTIFY_PROXIMO,
    TOOLTIP_CONFIGURACOES, TOOLTIP_CONFIG_VOLTAR,
    TEXTO_BUSCANDO_CLIMA, TEXTO_SEM_CONEXAO, FORMATO_VENTO_UMIDADE,
    UNIDADE_TEMPERATURA, DIAS_SEMANA, TEXTO_PROGRESSO_DIA, CIDADE,
    COR_BASE, COR_SUPERFICIE, COR_TEXTO, COR_TEXTO_SECUNDARIO, COR_TEXTO_TERCIARIO,
    COR_DESTAQUE, COR_BOTOES_SPOTIFY, OPACIDADE_FUNDO, PRESETS, RAIO_BORDA,
    MOSTRAR_CALENDARIO, MOSTRAR_SPOTIFY, MOSTRAR_ESPECTRO, MOSTRAR_PREVISAO,
    NOTIFICAR_CHUVA_FORTE, ADAPTAR_WALLPAPER_AUTO,
)
from css     import gerar_css
import weather  as mod_clima
import spotify  as mod_spotify
import wallpaper_theme as mod_wall
from spectrum import AudioSpectrum, N_BARS

log = logging.getLogger("widget")

# Limites da escala — evita janela minúscula ou enorme demais
_ESCALA_MIN = 0.80
_ESCALA_MAX = 1.30


def _escala_f() -> float:
    try:
        return max(_ESCALA_MIN, min(_ESCALA_MAX, float(ESCALA)))
    except Exception:
        return 1.0


def _px(n: float) -> int:
    """Converte px de design (escala 1.0) para o tamanho atual."""
    return max(1, int(round(float(n) * _escala_f())))


# Cores editáveis em config/colors.py (acima das derivações automáticas)
_CORES_EDITAVEIS = (
    ("COR_BASE",             "Fundo principal",          COR_BASE),
    ("COR_SUPERFICIE",       "Superfície dos botões",    COR_SUPERFICIE),
    ("COR_TEXTO",            "Texto principal",          COR_TEXTO),
    ("COR_TEXTO_SECUNDARIO", "Texto secundário",         COR_TEXTO_SECUNDARIO),
    ("COR_TEXTO_TERCIARIO",  "Texto terciário",          COR_TEXTO_TERCIARIO),
    ("COR_DESTAQUE",         "Destaque",                 COR_DESTAQUE),
    ("COR_BOTOES_SPOTIFY",   "Ícones dos controles",     COR_BOTOES_SPOTIFY),
)


def _hex_para_rgba(hex_cor: str) -> Gdk.RGBA:
    h = (hex_cor or "#ffffff").strip().lstrip("#")
    if len(h) != 6:
        h = "ffffff"
    rgba = Gdk.RGBA()
    rgba.red   = int(h[0:2], 16) / 255.0
    rgba.green = int(h[2:4], 16) / 255.0
    rgba.blue  = int(h[4:6], 16) / 255.0
    rgba.alpha = 1.0
    return rgba


def _rgba_para_hex(rgba: Gdk.RGBA) -> str:
    return (
        f"#{int(round(rgba.red * 255)):02x}"
        f"{int(round(rgba.green * 255)):02x}"
        f"{int(round(rgba.blue * 255)):02x}"
    )


class _BotaoMedia(Gtk.Button):
    """Controles prev/play/pause/next — Gtk.Button (visível sem python3-gi-cairo)."""

    _ICONES = {
        "play":  ICONE_SPOTIFY_REPRODUZIR,
        "pause": ICONE_SPOTIFY_PAUSAR,
        "prev":  ICONE_SPOTIFY_ANTERIOR,
        "next":  ICONE_SPOTIFY_PROXIMO,
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


class _EspectroBarras(Gtk.Box):
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

class _BotaoEngrenagem(Gtk.Button):
    """Botão de engrenagem — abre a tela de configurações."""

    def __init__(self, tooltip: str):
        super().__init__(label="⚙")
        self._aberto = False
        self._tooltip_abrir = tooltip
        self._tooltip_voltar = TOOLTIP_CONFIG_VOLTAR
        self.set_tooltip_text(tooltip)
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_focus_on_click(False)
        self.get_style_context().add_class("btnEngrenagem")

    def set_aberto(self, v: bool):
        self._aberto = v
        self.set_tooltip_text(self._tooltip_voltar if v else self._tooltip_abrir)
        ctx = self.get_style_context()
        if v:
            ctx.add_class("btnEngrenagemAtivo")
        else:
            ctx.remove_class("btnEngrenagemAtivo")


for _loc in ("pt_BR.UTF-8", "pt_BR", "pt_PT.UTF-8", "pt_PT", ""):
    try:
        locale.setlocale(locale.LC_TIME, _loc)
        break
    except locale.Error:
        continue


class WidgetDesktop(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._url_capa_atual  = None
        self._ls              = None
        self._pos_x           = 0
        self._pos_y           = 0
        self._pos_manual      = False
        self._arrastando      = False
        self._drag_off_x      = 0.0
        self._drag_off_y      = 0.0
        self._spotify_ocupado = False
        self._altura_atual    = 800
        self._espectro        = AudioSpectrum()
        self._cal_dia         = -1
        self._xprop_feito     = False
        self._css_provider    = None
        self._previsao_widgets = []
        self._wall_mtime = None
        self._wall_path_atual = None

        _cfg = Path(__file__).parent / "config"
        self._config_arquivos = [p for p in _cfg.glob("*.py") if not p.name.startswith("_")]
        self._config_mtimes   = {p: p.stat().st_mtime for p in self._config_arquivos}

        self._aplicar_css()
        self._configurar_janela()
        self._construir_ui()
        self._aplicar_visibilidade()
        self._aplicar_escala_widgets()
        self._iniciar_atualizacoes()
        self._espectro.start()

    # ── Configuração da janela ────────────────────────────────────────────

    def _aplicar_css(self):
        novo = Gtk.CssProvider()
        novo.load_from_data(gerar_css())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), novo,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        antigo, self._css_provider = self._css_provider, novo
        if antigo is not None:
            Gtk.StyleContext.remove_provider_for_screen(Gdk.Screen.get_default(), antigo)

    def _configurar_janela(self):
        self.set_title("Pop Spot")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_accept_focus(False)
        self.set_can_focus(False)

        tela   = self.get_screen()
        visual = tela.get_rgba_visual()
        if visual and tela.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)
        self._draw_fundo_id = self.connect("draw", self._desenhar_fundo)
        self.connect_after("realize", self._ao_realizar)
        self.connect_after("map", self._ao_mapear)

        display = Gdk.Display.get_default()
        self._monitor_geo = self._ler_monitor_geo()
        geo = self._monitor_geo
        px, py = self._carregar_posicao_arquivo()
        if px < 0 or py < 0:
            px, py = int(POS_X), int(POS_Y)
        # Posição salva de outra resolução fica fora da tela — ignora
        if px >= 0 and py >= 0 and not self._posicao_visivel(px, py, geo):
            log.info("posição salva fora da tela (%s,%s) — recentrando", px, py)
            try:
                (Path(__file__).parent / "config" / ".widget_pos").unlink(missing_ok=True)
            except Exception:
                pass
            px, py = -1, -1
        self._pos_manual = px >= 0 and py >= 0
        if self._pos_manual:
            self._pos_x, self._pos_y = self._clamp_pos(px, py)
        else:
            self._pos_x = self._calcular_pos_x(geo)
            self._pos_y = geo.y + (geo.height - self._altura_atual) // 2

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON_MOTION_MASK
            | Gdk.EventMask.STRUCTURE_MASK
        )
        self.connect("button-press-event", self._iniciar_arrasto)
        self.connect("motion-notify-event", self._durante_arrasto)
        self.connect("button-release-event", self._fim_arrasto)
        self.connect("configure-event", self._on_configure)
        try:
            display.connect("monitor-added", self._on_monitores_mudaram)
            display.connect("monitor-removed", self._on_monitores_mudaram)
        except Exception:
            pass
        try:
            tela.connect("size-changed", self._on_monitores_mudaram)
            tela.connect("monitors-changed", self._on_monitores_mudaram)
        except Exception:
            pass

        if self._ativar_layer_shell():
            log.info("gtk-layer-shell ativo (Wayland)")
        else:
            # X11/XWayland: UTILITY + skip_taskbar (COSMIC ainda pode listar no painel).
            try:
                self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            except Exception:
                pass
            self.set_keep_below(True)
            self.set_skip_taskbar_hint(True)
            self.set_skip_pager_hint(True)
            self.set_urgency_hint(False)
            self.stick()
            self.move(self._pos_x, self._pos_y)

    def _calcular_pos_x(self, geo, lado=None):
        lado = (lado or LADO or "direita").strip().lower()
        if lado.startswith("esq"):
            return geo.x + MARGEM_DIREITA
        return geo.x + geo.width - _px(LARGURA) - MARGEM_DIREITA

    @staticmethod
    def _ler_monitor_geo():
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        return monitor.get_geometry()

    def _posicao_visivel(self, x: int, y: int, geo=None) -> bool:
        """True se o canto do widget ainda cabe na tela atual."""
        geo = geo or self._monitor_geo
        w = max(self.get_allocated_width() or 0, _px(LARGURA))
        h = max(self.get_allocated_height() or 0, self._altura_atual)
        # Exige pelo menos ~60% do widget dentro da área útil
        return (
            x + w * 0.4 >= geo.x
            and y + h * 0.4 >= geo.y
            and x <= geo.x + geo.width - w * 0.4
            and y <= geo.y + geo.height - h * 0.4
        )

    def _on_monitores_mudaram(self, *_args):
        """Resolução/monitor mudou — atualiza geometria e reposiciona se preciso."""
        GLib.idle_add(self._reagir_mudanca_tela)
        return None

    def _reagir_mudanca_tela(self):
        antigo = self._monitor_geo
        geo = self._ler_monitor_geo()
        self._monitor_geo = geo
        if (
            antigo
            and antigo.width == geo.width
            and antigo.height == geo.height
            and antigo.x == geo.x
            and antigo.y == geo.y
        ):
            return False
        log.info(
            "tela mudou %sx%s → %sx%s",
            getattr(antigo, "width", "?"), getattr(antigo, "height", "?"),
            geo.width, geo.height,
        )
        # Coordenadas absolutas não transferem bem entre resoluções —
        # volta ao lado configurado (LADO) e esquece a posição manual.
        self._pos_manual = False
        try:
            (Path(__file__).parent / "config" / ".widget_pos").unlink(missing_ok=True)
        except Exception:
            pass
        x = self._calcular_pos_x(geo)
        y = geo.y + (geo.height - self._altura_atual) // 2
        self._mover_para(x, y)
        self._aplicar_input_shape()
        return False

    def _ao_mapear(self, *_args):
        if not self._ls:
            self._reforcar_x11()
        GLib.idle_add(self._finalizar_mapeamento)
        return False

    def _finalizar_mapeamento(self):
        """Único passo pós-map: reflow + input shape (sem spam de timeouts)."""
        self._monitor_geo = self._ler_monitor_geo()
        if self._pos_manual and not self._posicao_visivel(self._pos_x, self._pos_y):
            self._pos_manual = False
            try:
                (Path(__file__).parent / "config" / ".widget_pos").unlink(missing_ok=True)
            except Exception:
                pass
            geo = self._monitor_geo
            self._mover_para(
                self._calcular_pos_x(geo),
                geo.y + (geo.height - self._altura_atual) // 2,
            )
        elif self._pos_manual:
            self._mover_para(*self._clamp_pos(self._pos_x, self._pos_y))
        self.queue_resize()
        self._aplicar_input_shape()
        return False

    def _reforcar_x11(self):
        """Reforça hints de WM (skip taskbar/pager, below, sticky). xprop
        roda só uma vez — alguns WMs ignoram os hints do GDK antes do map."""
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.stick()
        if self._xprop_feito:
            return
        self._xprop_feito = True
        gw = self.get_window()
        if gw is None:
            return
        try:
            from gi.repository import GdkX11
            import subprocess
            xid = hex(GdkX11.X11Window.get_xid(gw))
            subprocess.run(
                ["xprop", "-id", xid, "-f", "_NET_WM_STATE", "32a", "-set", "_NET_WM_STATE",
                 "_NET_WM_STATE_SKIP_TASKBAR,_NET_WM_STATE_SKIP_PAGER,"
                 "_NET_WM_STATE_BELOW,_NET_WM_STATE_STICKY"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["xprop", "-id", xid, "-remove", "_NET_WM_STRUT", "-remove", "_NET_WM_STRUT_PARTIAL"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            log.debug("ewmh x11: %s", e)

    def _ao_realizar(self, *_args):
        try:
            self.set_decorated(False)
            gw = self.get_window()
            if gw is not None:
                if not self._ls:
                    self.set_skip_taskbar_hint(True)
                    self.set_skip_pager_hint(True)
                    try:
                        gw.set_decorations(Gdk.WMDecoration(0))
                        gw.set_functions(Gdk.WMFunction(0))
                        gw.set_type_hint(Gdk.WindowTypeHint.UTILITY)
                    except Exception:
                        pass
                try:
                    cur = (
                        Gdk.Cursor.new_from_name(gw.get_display(), "default")
                        or Gdk.Cursor.new_from_name(gw.get_display(), "left_ptr")
                    )
                    if cur is not None:
                        gw.set_cursor(cur)
                except Exception:
                    pass
        except Exception:
            pass
        GLib.idle_add(self._aplicar_input_shape)

    def _aplicar_input_shape(self):
        """Limita hits ao retângulo do widget (evita cursor/clique na mesa)."""
        gw = self.get_window()
        if gw is None:
            return False
        w = max(1, self.get_allocated_width() or _px(LARGURA))
        h = max(1, self.get_allocated_height() or self._altura_atual)
        try:
            import cairo
            region = cairo.Region(cairo.RectangleInt(0, 0, w, h))
            gw.input_shape_combine_region(region)
        except Exception as e:
            log.debug("input shape: %s", e)
        return False

    def _desenhar_fundo(self, _widget, cr):
        """Limpa o fundo e, no layer-shell, pinta o painel opaco (o CSS do
        .raiz nem sempre compõe sobre ARGB no COSMIC)."""
        try:
            try:
                import cairo as _cairo
            except ImportError:
                _cairo = None

            cr.set_source_rgba(0, 0, 0, 0)
            if _cairo is not None:
                cr.set_operator(_cairo.OPERATOR_SOURCE)
            else:
                cr.set_operator(1)
            cr.paint()

            if not self._ls:
                return False

            if _cairo is not None:
                cr.set_operator(_cairo.OPERATOR_OVER)

            if getattr(self, "_raiz", None) is not None:
                a = self._raiz.get_allocation()
                x, y, w, h = a.x, a.y, a.width, a.height
            else:
                x, y = 0, 0
                w = self.get_allocated_width() or _px(LARGURA)
                h = self.get_allocated_height() or self._altura_atual
            if w <= 1 or h <= 1:
                return False

            hx = (COR_BASE or "#0c0c12").lstrip("#")
            rf = int(hx[0:2], 16) / 255.0
            gf = int(hx[2:4], 16) / 255.0
            bf = int(hx[4:6], 16) / 255.0
            alpha = max(0.0, min(1.0, float(OPACIDADE_FUNDO)))
            raio = float(_px(RAIO_BORDA))
            self._caminho_arredondado(cr, x, y, w, h, raio)
            cr.set_source_rgba(rf, gf, bf, alpha)
            cr.fill()
        except TypeError:
            # Sem python3-gi-cairo o Context do GTK não chega ao Python
            try:
                self.disconnect(self._draw_fundo_id)
            except Exception:
                pass
        return False

    @staticmethod
    def _caminho_arredondado(cr, x, y, w, h, radius):
        r = max(0.0, min(radius, w / 2.0, h / 2.0))
        cr.new_path()
        cr.arc(x + w - r, y + r, r, -1.57079632679, 0)
        cr.arc(x + w - r, y + h - r, r, 0, 1.57079632679)
        cr.arc(x + r, y + h - r, r, 1.57079632679, 3.14159265359)
        cr.arc(x + r, y + r, r, 3.14159265359, 4.71238898038)
        cr.close_path()

    def _ativar_layer_shell(self):
        # BOTTOM + exclusive_zone=-1: acima do wallpaper, abaixo dos apps,
        # sem reservar borda (evita cursor de "clique" na mesa) nem taskbar.
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
            # NONE no desktop; EXCLUSIVE só com a tela de configs aberta.
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
            if hasattr(GtkLayerShell, "set_exclusive_zone"):
                GtkLayerShell.set_exclusive_zone(self, -1)
            return True
        except Exception:
            self._ls = None
            return False

    def _teclado_config(self, ativo: bool):
        """Liga teclado só nas configurações (layer-shell bloqueia com NONE)."""
        self.set_accept_focus(ativo)
        self.set_can_focus(ativo)
        if self._ls is not None:
            try:
                modo = (
                    self._ls.KeyboardMode.EXCLUSIVE if ativo
                    else self._ls.KeyboardMode.NONE
                )
                self._ls.set_keyboard_mode(self, modo)
            except Exception as e:
                log.debug("keyboard mode: %s", e)
        if ativo:
            try:
                self.present()
            except Exception:
                pass

    def _inicializar_altura(self, _widget):
        GLib.idle_add(self._medir_altura_natural)

    def _medir_altura_natural(self):
        _min, nat = self._raiz.get_preferred_height()
        h = nat + 20
        self._altura_atual = h
        self._raiz.set_size_request(_px(LARGURA), nat)
        self.set_size_request(_px(LARGURA), h)
        geo = self._monitor_geo or self._ler_monitor_geo()
        self._monitor_geo = geo
        if not self._pos_manual:
            self._pos_x = self._calcular_pos_x(geo)
            self._pos_y = geo.y + (geo.height - h) // 2
        else:
            self._pos_x, self._pos_y = self._clamp_pos(self._pos_x, self._pos_y)
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
        raiz.set_size_request(_px(LARGURA), -1)
        self._raiz = raiz

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(180)
        self._stack.set_homogeneous(False)
        self._stack.add_named(self._construir_pagina_principal(), "principal")
        self._stack.add_named(self._construir_pagina_config(), "config")
        self._stack.set_visible_child_name("principal")
        raiz.pack_start(self._stack, True, True, 0)

        # Rodapé — engrenagem alinhada à direita
        rodape = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        rodape.set_halign(Gtk.Align.FILL)
        rodape.set_margin_top(10)
        self.btn_config = _BotaoEngrenagem(TOOLTIP_CONFIGURACOES)
        self.btn_config.connect("clicked", self._on_toggle_config)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        rodape.pack_start(spacer, True, True, 0)
        rodape.pack_start(self.btn_config, False, False, 0)
        raiz.pack_start(rodape, False, False, 0)

        self.connect("map", self._inicializar_altura)
        self.add(raiz)

    def _tornar_clicavel(self, widget):
        """Envolve um widget num EventBox clicável, sem disparar arrasto da janela."""
        caixa = Gtk.EventBox()
        caixa.set_visible_window(False)
        caixa.add(widget)
        caixa._pop_spot_no_drag = True
        caixa.connect("button-press-event", self._on_clique_spotify)
        return caixa

    def _on_clique_spotify(self, _widget, event):
        if event.button == 1:
            threading.Thread(target=mod_spotify.abrir, daemon=True).start()
            return True
        return False

    def _construir_pagina_principal(self):
        pagina = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

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
        pagina.pack_start(caixa_relogio, False, False, 0)

        pagina.pack_start(self._separador(), False, False, 0)

        # Clima
        caixa_clima = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        linha_temp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.img_icone_clima = Gtk.Image()
        self.img_icone_clima.get_style_context().add_class("iconeClima")
        self.img_icone_clima.set_size_request(36, 36)
        self.img_icone_clima.set_valign(Gtk.Align.CENTER)
        self._codigo_clima_atual = None
        self._atualizar_icone_clima(None)  # sol padrão enquanto carrega
        self.lbl_temperatura = self._rotulo("temperaturaClima", "--°C", Gtk.Align.START)
        linha_temp.pack_start(self.img_icone_clima, False, False, 0)
        linha_temp.pack_start(self.lbl_temperatura, False, False, 0)
        caixa_clima.pack_start(linha_temp, False, False, 0)

        self.lbl_cidade    = self._rotulo("cidadeClima",    "--",               Gtk.Align.START)
        self.lbl_descricao = self._rotulo("descricaoClima", TEXTO_BUSCANDO_CLIMA, Gtk.Align.START)
        self.lbl_detalhe   = self._rotulo("detalheClima",   "",                 Gtk.Align.START)
        for w in (self.lbl_cidade, self.lbl_descricao, self.lbl_detalhe):
            caixa_clima.pack_start(w, False, False, 0)

        caixa_clima.pack_start(self._construir_previsao(), False, False, 6)

        pagina.pack_start(caixa_clima, False, False, 0)
        pagina.pack_start(self._separador(), False, False, 0)

        # Spotify
        caixa_spotify = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._caixa_spotify = caixa_spotify

        linha_cabecalho = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.img_nota_spotify = Gtk.Image()
        self.img_nota_spotify.set_valign(Gtk.Align.CENTER)
        self._atualizar_nota_spotify()
        self.lbl_cabecalho_spotify = self._rotulo("cabecalhoSpotify", TEXTO_TOCANDO, Gtk.Align.START)
        linha_cabecalho.pack_start(self._tornar_clicavel(self.img_nota_spotify), False, False, 0)
        linha_cabecalho.pack_start(self.lbl_cabecalho_spotify, False, False, 0)
        caixa_spotify.pack_start(linha_cabecalho, False, False, 0)

        self.img_capa = Gtk.Image()
        self.img_capa.set_size_request(_px(TAMANHO_CAPA), _px(TAMANHO_CAPA))
        envoltorio_capa = self._tornar_clicavel(self.img_capa)
        envoltorio_capa.set_halign(Gtk.Align.START)
        caixa_spotify.pack_start(envoltorio_capa, False, False, 8)

        linha_ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        linha_ctrl.set_halign(Gtk.Align.START)
        self.btn_spotify_prev = _BotaoMedia("prev", TOOLTIP_SPOTIFY_ANTERIOR)
        self.btn_spotify_prev.connect("clicked", self._on_spotify_prev)
        self.btn_spotify_play = _BotaoMedia("play", TOOLTIP_SPOTIFY_PLAY)
        self.btn_spotify_play.connect("clicked", self._on_spotify_play_pause)
        self.btn_spotify_next = _BotaoMedia("next", TOOLTIP_SPOTIFY_PROXIMO)
        self.btn_spotify_next.connect("clicked", self._on_spotify_next)
        for b in (self.btn_spotify_prev, self.btn_spotify_play, self.btn_spotify_next):
            linha_ctrl.pack_start(b, False, False, 0)

        self._volume_syncing = False
        self.scale_volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale_volume.set_draw_value(False)
        self.scale_volume.set_size_request(88, -1)
        self.scale_volume.set_valign(Gtk.Align.CENTER)
        self.scale_volume.set_tooltip_text("Volume")
        self.scale_volume.get_style_context().add_class("scaleVolume")
        self.scale_volume.set_sensitive(False)
        self.scale_volume.connect("value-changed", self._on_volume_changed)
        linha_ctrl.pack_start(self.scale_volume, False, False, 4)

        caixa_spotify.pack_start(linha_ctrl, False, False, 8)

        self.lbl_titulo     = self._rotulo("tituloMusica",  "", Gtk.Align.START, reticencias=True)
        self.lbl_artista    = self._rotulo("artistaMusica", "", Gtk.Align.START, reticencias=True)
        self.lbl_album      = self._rotulo("albumMusica",   "", Gtk.Align.START, reticencias=True)
        self.lbl_sem_musica = self._rotulo("semMusica", TEXTO_SEM_SPOTIFY, Gtk.Align.START)

        caixa_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for w in (self.lbl_titulo, self.lbl_artista, self.lbl_album):
            caixa_info.pack_start(w, False, False, 0)

        self.espectro_area = _EspectroBarras()

        linha_musica = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        linha_musica.pack_start(caixa_info,         True,  True,  0)
        linha_musica.pack_start(self.espectro_area, False, False, 0)

        caixa_spotify.pack_start(linha_musica,       False, False, 0)
        caixa_spotify.pack_start(self.lbl_sem_musica, False, False, 0)

        pagina.pack_start(caixa_spotify, False, False, 0)
        return pagina

    def _construir_previsao(self):
        """Linha com previsão de 3 dias: dia + ícone 20px + mín/máx."""
        caixa = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caixa.set_homogeneous(True)
        self._previsao_widgets = []
        for _ in range(3):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col.set_halign(Gtk.Align.START)
            lbl_dia = self._rotulo("previsaoDia", "", Gtk.Align.START)
            img = Gtk.Image()
            img.set_size_request(20, 20)
            lbl_temp = self._rotulo("previsaoTemp", "", Gtk.Align.START)
            col.pack_start(lbl_dia, False, False, 0)
            col.pack_start(img, False, False, 0)
            col.pack_start(lbl_temp, False, False, 0)
            caixa.pack_start(col, True, True, 0)
            self._previsao_widgets.append((lbl_dia, img, lbl_temp))
        self._caixa_previsao = caixa
        return caixa

    # ── Tela de configurações ─────────────────────────────────────────────

    def _construir_pagina_config(self):
        pagina = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        pagina.pack_start(
            self._rotulo("tituloConfig", "CONFIGURAÇÕES", Gtk.Align.START), False, False, 0)
        pagina.pack_start(
            self._rotulo(
                "dicaConfig", "Alterações aplicam sem reiniciar.", Gtk.Align.START),
            False, False, 0,
        )

        conteudo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        conteudo.pack_start(self._separador(), False, False, 0)

        conteudo.pack_start(
            self._rotulo("labelConfig", "Cidade do clima", Gtk.Align.START), False, False, 0)
        self.entry_cidade = Gtk.Entry()
        self.entry_cidade.set_text(CIDADE or "")
        self.entry_cidade.set_placeholder_text("Vazio = detectar automaticamente")
        self.entry_cidade.get_style_context().add_class("entryConfig")
        self._cidade_store = Gtk.ListStore(str, str)  # rótulo, cidade
        self._cidade_completion = Gtk.EntryCompletion()
        self._cidade_completion.set_model(self._cidade_store)
        self._cidade_completion.set_text_column(0)
        self._cidade_completion.set_inline_completion(False)
        self._cidade_completion.set_popup_completion(True)
        self._cidade_completion.set_minimum_key_length(2)
        self._cidade_completion.set_match_func(self._cidade_match_sempre)
        self._cidade_completion.connect("match-selected", self._on_cidade_escolhida)
        self.entry_cidade.set_completion(self._cidade_completion)
        self._cidade_suggest_id = 0
        self.entry_cidade.connect("changed", self._on_cidade_digitando)
        linha_cidade = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        linha_cidade.pack_start(self.entry_cidade, True, True, 0)
        btn_auto = Gtk.Button(label="Automático")
        btn_auto.set_tooltip_text("Limpa o campo e usa sua localização")
        btn_auto.get_style_context().add_class("btnConfigSec")
        btn_auto.connect("clicked", self._on_cidade_automatica)
        linha_cidade.pack_start(btn_auto, False, False, 0)
        conteudo.pack_start(linha_cidade, False, False, 0)
        conteudo.pack_start(
            self._rotulo(
                "dicaConfig",
                "Digite para ver sugestões. Vazio = automático.\n"
                "Escolha na lista e clique em Salvar.",
                Gtk.Align.START,
            ),
            False, False, 0,
        )

        self.chk_chuva = Gtk.CheckButton(label="Avisar chuva forte (notificação)")
        self.chk_chuva.set_active(bool(NOTIFICAR_CHUVA_FORTE))
        self.chk_chuva.get_style_context().add_class("checkConfig")
        conteudo.pack_start(self.chk_chuva, False, False, 0)

        conteudo.pack_start(
            self._rotulo("labelConfig", "Unidade de temperatura", Gtk.Align.START), False, False, 0)

        self._unidade_group = Gtk.RadioButton.new_with_label(None, "°C")
        self._unidade_group.get_style_context().add_class("radioConfig")
        radio_f = Gtk.RadioButton.new_with_label_from_widget(self._unidade_group, "°F")
        radio_f.get_style_context().add_class("radioConfig")
        if UNIDADE_TEMPERATURA.strip().upper() in ("°F", "F"):
            radio_f.set_active(True)
        else:
            self._unidade_group.set_active(True)
        self._radio_f = radio_f

        linha_unid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        linha_unid.pack_start(self._unidade_group, False, False, 0)
        linha_unid.pack_start(radio_f, False, False, 0)
        conteudo.pack_start(linha_unid, False, False, 0)

        conteudo.pack_start(
            self._rotulo("labelConfig", "Lado da tela", Gtk.Align.START), False, False, 0)
        self._lado_group = Gtk.RadioButton.new_with_label(None, "Direita")
        self._lado_group.get_style_context().add_class("radioConfig")
        radio_esq = Gtk.RadioButton.new_with_label_from_widget(self._lado_group, "Esquerda")
        radio_esq.get_style_context().add_class("radioConfig")
        if str(LADO).strip().lower().startswith("esq"):
            radio_esq.set_active(True)
        else:
            self._lado_group.set_active(True)
        self._radio_esq = radio_esq
        linha_lado = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        linha_lado.pack_start(self._lado_group, False, False, 0)
        linha_lado.pack_start(radio_esq, False, False, 0)
        conteudo.pack_start(linha_lado, False, False, 0)

        conteudo.pack_start(self._separador(), False, False, 0)
        conteudo.pack_start(
            self._rotulo("tituloConfig", "BLOCOS VISÍVEIS", Gtk.Align.START), False, False, 0)

        caixa_blocos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.chk_calendario = Gtk.CheckButton(label="Calendário e progresso do dia")
        self.chk_spotify    = Gtk.CheckButton(label="Spotify")
        self.chk_espectro   = Gtk.CheckButton(label="Espectro de áudio")
        self.chk_previsao   = Gtk.CheckButton(label="Previsão de 3 dias")
        for chk, atual in (
            (self.chk_calendario, MOSTRAR_CALENDARIO),
            (self.chk_spotify,    MOSTRAR_SPOTIFY),
            (self.chk_espectro,   MOSTRAR_ESPECTRO),
            (self.chk_previsao,   MOSTRAR_PREVISAO),
        ):
            chk.set_active(bool(atual))
            chk.get_style_context().add_class("checkConfig")
            caixa_blocos.pack_start(chk, False, False, 0)
        conteudo.pack_start(caixa_blocos, False, False, 0)

        conteudo.pack_start(self._separador(), False, False, 0)
        conteudo.pack_start(
            self._rotulo("tituloConfig", "CORES", Gtk.Align.START), False, False, 0)

        # Presets
        conteudo.pack_start(
            self._rotulo("labelConfig", "Tema rápido", Gtk.Align.START), False, False, 0)
        linha_presets = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        linha_presets.set_homogeneous(True)
        for nome_preset in PRESETS:
            bp = Gtk.Button(label=nome_preset)
            bp.get_style_context().add_class("btnConfigSec")
            bp.connect("clicked", self._on_aplicar_preset, nome_preset)
            linha_presets.pack_start(bp, True, True, 0)
        conteudo.pack_start(linha_presets, False, False, 0)

        btn_wall = Gtk.Button(label="Adaptar ao wallpaper")
        btn_wall.set_tooltip_text("Extrai cores do fundo de tela atual (COSMIC)")
        btn_wall.get_style_context().add_class("btnConfig")
        btn_wall.connect("clicked", self._on_adaptar_wallpaper)
        conteudo.pack_start(btn_wall, False, False, 0)

        self.chk_wall_auto = Gtk.CheckButton(label="Atualizar cores quando o wallpaper mudar")
        self.chk_wall_auto.set_active(bool(ADAPTAR_WALLPAPER_AUTO))
        self.chk_wall_auto.get_style_context().add_class("checkConfig")
        conteudo.pack_start(self.chk_wall_auto, False, False, 0)
        conteudo.pack_start(
            self._rotulo(
                "dicaConfig",
                "Usa as cores dominantes do wallpaper.\n"
                "Salvar grava o tema (e a opção automática).",
                Gtk.Align.START,
            ),
            False, False, 0,
        )

        conteudo.pack_start(
            self._rotulo("labelConfig", "Tamanho do widget", Gtk.Align.START), False, False, 0)
        self.scale_tamanho = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, _ESCALA_MIN, _ESCALA_MAX, 0.05)
        self.scale_tamanho.set_value(float(_escala_f()))
        self.scale_tamanho.set_draw_value(True)
        self.scale_tamanho.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_tamanho.set_digits(2)
        self.scale_tamanho.get_style_context().add_class("scaleConfig")
        conteudo.pack_start(self.scale_tamanho, False, False, 0)
        conteudo.pack_start(
            self._rotulo(
                "dicaConfig",
                "80%–130%. Fontes, botões e ícones acompanham.",
                Gtk.Align.START,
            ),
            False, False, 0,
        )

        # Opacidade
        conteudo.pack_start(
            self._rotulo("labelConfig", "Opacidade do fundo", Gtk.Align.START), False, False, 0)
        self.scale_opacidade = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.40, 1.0, 0.01)
        self.scale_opacidade.set_value(float(OPACIDADE_FUNDO))
        self.scale_opacidade.set_draw_value(True)
        self.scale_opacidade.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_opacidade.set_digits(2)
        self.scale_opacidade.get_style_context().add_class("scaleConfig")
        conteudo.pack_start(self.scale_opacidade, False, False, 0)

        conteudo.pack_start(
            self._rotulo(
                "dicaConfig",
                "Secundário: clima, artista, calendário, progresso.\n"
                "Terciário: vento/umidade e álbum.",
                Gtk.Align.START,
            ),
            False, False, 0,
        )

        self._cores_botoes = {}
        for nome, rotulo, valor in _CORES_EDITAVEIS:
            hex_val = valor if str(valor).startswith("#") else f"#{valor}"
            linha = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = self._rotulo("labelConfig", rotulo, Gtk.Align.START)
            lbl.set_hexpand(True)
            lbl.set_xalign(0.0)

            entry = Gtk.Entry()
            entry.set_text(hex_val)
            entry.set_max_length(7)
            entry.set_width_chars(8)
            entry.set_placeholder_text("#rrggbb")
            entry.get_style_context().add_class("entryConfig")
            entry.get_style_context().add_class("entryHex")

            btn = Gtk.ColorButton.new_with_rgba(_hex_para_rgba(hex_val))
            btn.set_title(rotulo)
            btn.set_use_alpha(False)
            btn.get_style_context().add_class("btnCor")
            btn.set_size_request(36, 28)

            self._cores_botoes[nome] = btn
            self._cores_botoes[nome + "_entry"] = entry
            btn.connect("color-set", self._on_cor_picker, nome)
            entry.connect("changed", self._on_cor_entry, nome)

            linha.pack_start(lbl, True, True, 0)
            linha.pack_end(btn, False, False, 0)
            linha.pack_end(entry, False, False, 0)
            conteudo.pack_start(linha, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_propagate_natural_height(True)
        scroll.set_max_content_height(460)
        scroll.add(conteudo)
        pagina.pack_start(scroll, True, True, 0)

        self.lbl_status_config = self._rotulo("statusConfig", "", Gtk.Align.START)

        btn_salvar = Gtk.Button(label="Salvar")
        btn_salvar.get_style_context().add_class("btnConfig")
        btn_salvar.connect("clicked", self._on_salvar_config)

        btn_pasta = Gtk.Button(label="Abrir pasta config")
        btn_pasta.get_style_context().add_class("btnConfigSec")
        btn_pasta.connect("clicked", self._on_abrir_pasta_config)

        linha_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        linha_btns.pack_start(btn_salvar, False, False, 0)
        linha_btns.pack_start(btn_pasta, False, False, 0)
        pagina.pack_start(linha_btns, False, False, 4)
        pagina.pack_start(self.lbl_status_config, False, False, 0)

        return pagina

    def _on_cor_picker(self, btn, nome):
        hex_cor = _rgba_para_hex(btn.get_rgba())
        entry = self._cores_botoes.get(nome + "_entry")
        if entry is not None:
            entry.handler_block_by_func(self._on_cor_entry)
            entry.set_text(hex_cor)
            entry.handler_unblock_by_func(self._on_cor_entry)

    def _on_cor_entry(self, entry, nome):
        texto = entry.get_text().strip()
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", texto):
            return
        btn = self._cores_botoes.get(nome)
        if btn is None:
            return
        btn.handler_block_by_func(self._on_cor_picker)
        btn.set_rgba(_hex_para_rgba(texto))
        btn.handler_unblock_by_func(self._on_cor_picker)

    def _on_aplicar_preset(self, _btn, nome_preset):
        preset = PRESETS.get(nome_preset)
        if not preset:
            return
        self._preencher_cores_ui(preset)
        self.lbl_status_config.set_text(f"Tema “{nome_preset}” aplicado — Salvar para confirmar")

    def _preencher_cores_ui(self, cores: dict):
        for nome, valor in cores.items():
            if nome == "OPACIDADE_FUNDO":
                if hasattr(self, "scale_opacidade"):
                    self.scale_opacidade.set_value(float(valor))
                continue
            if not isinstance(valor, str) or not valor.startswith("#"):
                continue
            btn = self._cores_botoes.get(nome)
            entry = self._cores_botoes.get(nome + "_entry")
            if btn is not None:
                btn.set_rgba(_hex_para_rgba(valor))
            if entry is not None:
                entry.set_text(valor)

    def _on_adaptar_wallpaper(self, _btn):
        self.lbl_status_config.set_text("Lendo wallpaper…")
        threading.Thread(target=self._bg_adaptar_wallpaper, daemon=True).start()

    def _bg_adaptar_wallpaper(self):
        tema, info = mod_wall.adaptar_ao_wallpaper()
        GLib.idle_add(self._aplicar_tema_wallpaper, tema, info)

    def _aplicar_tema_wallpaper(self, tema, info):
        if not tema:
            self.lbl_status_config.set_text(info or "Não foi possível adaptar")
            return False
        self._preencher_cores_ui(tema)
        nome = Path(info).name if info else "wallpaper"
        self.lbl_status_config.set_text(f"Cores de “{nome}” — Salvar para confirmar")
        self._wall_path_atual = info
        return False

    def _gravar_e_aplicar_tema(self, tema: dict):
        """Grava colors.py com o tema e recarrega ao vivo."""
        cores = {k: v for k, v in tema.items() if k.startswith("COR_") or k == "OPACIDADE_FUNDO"}
        self._gravar_constantes(Path(__file__).parent / "config" / "colors.py", cores)
        self._recarregar_config()

    def _carregar_cores_ui(self):
        atuais = {
            "COR_BASE": COR_BASE,
            "COR_SUPERFICIE": COR_SUPERFICIE,
            "COR_TEXTO": COR_TEXTO,
            "COR_TEXTO_SECUNDARIO": COR_TEXTO_SECUNDARIO,
            "COR_TEXTO_TERCIARIO": COR_TEXTO_TERCIARIO,
            "COR_DESTAQUE": COR_DESTAQUE,
            "COR_BOTOES_SPOTIFY": COR_BOTOES_SPOTIFY,
        }
        # Relê do arquivo para pegar valores gravados (antes do hot-reload)
        arq = Path(__file__).parent / "config" / "colors.py"
        opacidade = float(OPACIDADE_FUNDO)
        try:
            texto = arq.read_text(encoding="utf-8")
            for nome in list(atuais):
                m = re.search(rf"^{re.escape(nome)}\s*=\s*(.+)$", texto, re.M)
                if not m:
                    continue
                raw = m.group(1).strip()
                if raw.startswith(("'", '"')):
                    atuais[nome] = raw.strip("'\"")
                elif raw in atuais:
                    atuais[nome] = atuais[raw]
            m_op = re.search(r"^OPACIDADE_FUNDO\s*=\s*([0-9.]+)", texto, re.M)
            if m_op:
                opacidade = float(m_op.group(1))
        except Exception:
            pass

        if hasattr(self, "scale_opacidade"):
            self.scale_opacidade.set_value(opacidade)

        for nome, valor in atuais.items():
            if not isinstance(valor, str) or not valor.startswith("#"):
                continue
            btn = self._cores_botoes.get(nome)
            entry = self._cores_botoes.get(nome + "_entry")
            if btn is not None:
                btn.set_rgba(_hex_para_rgba(valor))
            if entry is not None:
                entry.set_text(valor)

    def _on_toggle_config(self, _widget):
        aberto = self._stack.get_visible_child_name() == "config"
        if aberto:
            self._stack.set_visible_child_name("principal")
            self.btn_config.set_aberto(False)
            self._teclado_config(False)
        else:
            self.entry_cidade.set_text(CIDADE or "")
            self._carregar_cores_ui()
            for chk, atual in (
                (self.chk_calendario, MOSTRAR_CALENDARIO),
                (self.chk_spotify,    MOSTRAR_SPOTIFY),
                (self.chk_espectro,   MOSTRAR_ESPECTRO),
                (self.chk_previsao,   MOSTRAR_PREVISAO),
            ):
                chk.set_active(bool(atual))
            if hasattr(self, "chk_chuva"):
                self.chk_chuva.set_active(bool(NOTIFICAR_CHUVA_FORTE))
            if hasattr(self, "chk_wall_auto"):
                self.chk_wall_auto.set_active(bool(ADAPTAR_WALLPAPER_AUTO))
            if hasattr(self, "scale_tamanho"):
                self.scale_tamanho.set_value(float(_escala_f()))
            self._stack.set_visible_child_name("config")
            self.btn_config.set_aberto(True)
            self.lbl_status_config.set_text("")
            self._teclado_config(True)
            self.entry_cidade.set_can_focus(True)
            GLib.idle_add(self._focar_cidade)
        GLib.idle_add(self._medir_altura_natural)
        return True

    def _focar_cidade(self):
        try:
            self.entry_cidade.grab_focus()
            self.entry_cidade.grab_focus_without_selecting()
        except Exception:
            try:
                self.entry_cidade.grab_focus()
            except Exception:
                pass
        return False

    def _on_cidade_automatica(self, _btn):
        self._teclado_config(True)
        self.entry_cidade.set_text("")
        self._cidade_store.clear()
        GLib.idle_add(self._focar_cidade)
        self.lbl_status_config.set_text("Automático — clique em Salvar para aplicar")

    def _on_cidade_digitando(self, entry):
        if getattr(self, "_cidade_suggest_id", 0):
            GLib.source_remove(self._cidade_suggest_id)
        texto = entry.get_text().strip()
        if len(texto) < 2:
            self._cidade_store.clear()
            self._cidade_suggest_id = 0
            return
        self._cidade_suggest_id = GLib.timeout_add(350, self._buscar_sugestoes_cidade, texto)

    def _buscar_sugestoes_cidade(self, texto):
        self._cidade_suggest_id = 0
        # Confirma que o texto ainda é o atual
        if self.entry_cidade.get_text().strip() != texto:
            return False
        threading.Thread(
            target=self._bg_sugestoes_cidade, args=(texto,), daemon=True).start()
        return False

    def _bg_sugestoes_cidade(self, texto):
        sugestoes = mod_clima.sugerir_cidades(texto)
        GLib.idle_add(self._aplicar_sugestoes_cidade, texto, sugestoes)

    def _aplicar_sugestoes_cidade(self, texto, sugestoes):
        if self.entry_cidade.get_text().strip() != texto:
            return False
        self._cidade_store.clear()
        for s in sugestoes:
            self._cidade_store.append([s["rotulo"], s["cidade"]])
        return False

    def _on_cidade_escolhida(self, _completion, model, tree_iter):
        cidade = model[tree_iter][1]
        self.entry_cidade.set_text(cidade)
        self.entry_cidade.set_position(-1)
        return True

    @staticmethod
    def _cidade_match_sempre(_completion, _key, _it, *_a):
        """Mostra todos os resultados da API (já filtrados)."""
        return True

    def _on_abrir_pasta_config(self, _btn):
        pasta = Path(__file__).parent / "config"
        try:
            from gi.repository import Gio
            Gio.AppInfo.launch_default_for_uri(pasta.as_uri(), None)
        except Exception:
            os.system(f'xdg-open "{pasta}" >/dev/null 2>&1 &')

    def _on_salvar_config(self, _btn):
        cidade = self.entry_cidade.get_text().strip()
        unidade = "°F" if self._radio_f.get_active() else "°C"
        lado = "esquerda" if self._radio_esq.get_active() else "direita"
        opacidade = round(float(self.scale_opacidade.get_value()), 2)
        escala = round(float(self.scale_tamanho.get_value()), 2)
        escala = max(_ESCALA_MIN, min(_ESCALA_MAX, escala))
        cores = {}
        for nome, _rotulo, _padrao in _CORES_EDITAVEIS:
            entry = self._cores_botoes.get(nome + "_entry")
            btn = self._cores_botoes.get(nome)
            hex_cor = entry.get_text().strip() if entry is not None else ""
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", hex_cor, flags=re.I):
                hex_cor = _rgba_para_hex(btn.get_rgba()) if btn is not None else "#ffffff"
            cores[nome] = hex_cor.lower()
        cores["OPACIDADE_FUNDO"] = opacidade

        try:
            self._gravar_constantes(
                Path(__file__).parent / "config" / "personalizar.py",
                {
                    "CIDADE": cidade,
                    "UNIDADE_TEMPERATURA": unidade,
                    "MOSTRAR_CALENDARIO": self.chk_calendario.get_active(),
                    "MOSTRAR_SPOTIFY": self.chk_spotify.get_active(),
                    "MOSTRAR_ESPECTRO": self.chk_espectro.get_active(),
                    "MOSTRAR_PREVISAO": self.chk_previsao.get_active(),
                    "NOTIFICAR_CHUVA_FORTE": self.chk_chuva.get_active(),
                    "ADAPTAR_WALLPAPER_AUTO": (
                        self.chk_wall_auto.get_active()
                        if hasattr(self, "chk_wall_auto") else False
                    ),
                },
            )
            self._gravar_constantes(
                Path(__file__).parent / "config" / "colors.py",
                cores,
            )
            self._gravar_constantes(
                Path(__file__).parent / "config" / "layout.py",
                {"LADO": lado, "POS_X": -1, "POS_Y": -1, "ESCALA": escala},
            )
            # Limpa posição manual salva para o LADO voltar a valer
            try:
                (Path(__file__).parent / "config" / ".widget_pos").unlink(missing_ok=True)
            except Exception:
                pass
            self._recarregar_config()
            mod_clima.limpar_cache_clima()
            threading.Thread(target=self._bg_clima, daemon=True).start()
            self.lbl_status_config.set_text("Salvo")
        except Exception as e:
            self.lbl_status_config.set_text(f"Erro ao salvar: {e}")
            log.exception("salvar config")

    @staticmethod
    def _gravar_constantes(caminho: Path, valores: dict):
        texto = caminho.read_text(encoding="utf-8")
        for nome, valor in valores.items():
            if isinstance(valor, bool):
                literal = "True" if valor else "False"
            elif isinstance(valor, str):
                literal = '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'
            elif isinstance(valor, float):
                literal = f"{valor:.2f}"
            else:
                literal = repr(valor)
            padrao = rf"^({re.escape(nome)}\s*=\s*).*$"
            novo, n = re.subn(padrao, rf"\g<1>{literal}", texto, count=1, flags=re.M)
            if n == 0:
                raise ValueError(f"constante {nome} não encontrada em {caminho.name}")
            texto = novo
        caminho.write_text(texto, encoding="utf-8")

    # ── Config viva (sem reiniciar) ────────────────────────────────────────

    def _recarregar_config(self):
        """Recarrega módulos de config/css, atualiza globais e reaplica tudo."""
        import importlib
        import config.colors, config.personalizar, config.layout, config, css
        try:
            importlib.reload(config.colors)
            importlib.reload(config.personalizar)
            importlib.reload(config.layout)
            importlib.reload(config)
            importlib.reload(css)
        except Exception as e:
            log.exception("recarregar config: %s", e)
            return

        global gerar_css
        from css import gerar_css

        g = globals()
        for k in dir(config):
            if k.isupper():
                g[k] = getattr(config, k)

        self._aplicar_css()
        self._aplicar_visibilidade()
        self._aplicar_escala_widgets()
        self._atualizar_nota_spotify()
        codigo = getattr(self, "_codigo_clima_atual", None)
        if codigo is not None:
            self._atualizar_icone_clima(codigo)
        if self._url_capa_atual:
            threading.Thread(
                target=self._bg_capa, args=(self._url_capa_atual,), daemon=True).start()
        mod_clima.limpar_cache_localizacao()
        threading.Thread(target=self._bg_clima, daemon=True).start()
        self._config_mtimes = {p: p.stat().st_mtime for p in self._config_arquivos}
        self.queue_draw()
        GLib.idle_add(self._medir_altura_natural)

    def _aplicar_escala_widgets(self):
        """Reajusta size_requests e mídias conforme ESCALA (seguro, sem rebuild)."""
        w = _px(LARGURA)
        capa = _px(TAMANHO_CAPA)
        if getattr(self, "_raiz", None) is not None:
            self._raiz.set_size_request(w, -1)
        self.set_size_request(w, max(self._altura_atual, 100))

        for b in (
            getattr(self, "btn_spotify_prev", None),
            getattr(self, "btn_spotify_play", None),
            getattr(self, "btn_spotify_next", None),
        ):
            if b is not None:
                b.definir_tamanho(_px(52), _px(30))

        if getattr(self, "espectro_area", None) is not None:
            self.espectro_area.definir_tamanho(_px(95), _px(55))
        if getattr(self, "img_icone_clima", None) is not None:
            self.img_icone_clima.set_size_request(_px(36), _px(36))
        if getattr(self, "img_capa", None) is not None:
            self.img_capa.set_size_request(capa, capa)
        if getattr(self, "scale_volume", None) is not None:
            self.scale_volume.set_size_request(_px(88), -1)
        if getattr(self, "_painel_dir", None) is not None:
            self._painel_dir.set_size_request(_px(95), -1)
        if getattr(self, "btn_config", None) is not None:
            self.btn_config.set_size_request(_px(32), _px(32))
        for _lbl_dia, img, _lbl_temp in getattr(self, "_previsao_widgets", []):
            img.set_size_request(_px(20), _px(20))
        # Re-render nota na escala atual
        try:
            from weather_icons import renderizar_nota
            if getattr(self, "img_nota_spotify", None) is not None:
                self.img_nota_spotify.set_from_pixbuf(
                    renderizar_nota(tamanho=_px(16), cor=COR_DESTAQUE))
        except Exception:
            pass

    def _aplicar_visibilidade(self):
        self._cal_grid.set_visible(bool(MOSTRAR_CALENDARIO))
        self._caixa_spotify.set_visible(bool(MOSTRAR_SPOTIFY))
        self.espectro_area.set_visible(bool(MOSTRAR_ESPECTRO))
        self._caixa_previsao.set_visible(bool(MOSTRAR_PREVISAO))

    def _atualizar_nota_spotify(self):
        try:
            from weather_icons import renderizar_nota
            self.img_nota_spotify.set_from_pixbuf(
                renderizar_nota(tamanho=_px(16), cor=COR_DESTAQUE))
        except Exception as e:
            log.debug("nota spotify: %s", e)

    # ── Painel direito do relógio (progresso + calendário) ────────────────

    def _construir_painel_dir(self):
        painel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        painel.set_valign(Gtk.Align.CENTER)
        painel.set_size_request(95, -1)
        self._painel_dir = painel

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

    def _eh_controle_interativo(self, widget) -> bool:
        """True se o clique foi em botão/campo/checkbox (não deve iniciar arrasto)."""
        w = widget
        while w is not None:
            if getattr(w, "_pop_spot_no_drag", False):
                return True
            if isinstance(
                w,
                (Gtk.Button, Gtk.Entry, Gtk.RadioButton, Gtk.CheckButton, Gtk.ColorButton,
                 Gtk.Scale, Gtk.SpinButton, _BotaoMedia, _BotaoEngrenagem),
            ):
                return True
            w = w.get_parent()
        return False

    def _clamp_pos(self, x: int, y: int) -> tuple[int, int]:
        geo = self._monitor_geo or self._ler_monitor_geo()
        w = max(self.get_allocated_width() or 0, _px(LARGURA))
        h = max(self.get_allocated_height() or 0, self._altura_atual)
        max_x = max(geo.x, geo.x + geo.width - w)
        max_y = max(geo.y, geo.y + geo.height - h)
        x = max(geo.x, min(x, max_x))
        y = max(geo.y, min(y, max_y))
        return int(x), int(y)

    # ── Arrasto e menu de contexto ─────────────────────────────────────────

    def _iniciar_arrasto(self, widget, event):
        """Botão 1 arrasta a janela; botão 3 abre o menu de contexto."""
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return False
        alvo = Gtk.get_event_widget(event)

        if event.button == 3:
            if alvo and self._eh_controle_interativo(alvo):
                return False
            self._mostrar_menu_contexto(event)
            return True

        if event.button != 1:
            return False
        if alvo and self._eh_controle_interativo(alvo):
            return False
        if getattr(self, "_stack", None) and self._stack.get_visible_child_name() == "config":
            return False

        # X11: arrasto nativo do compositor (confiável no COSMIC/XWayland)
        if not self._ls:
            try:
                self.begin_move_drag(
                    event.button, int(event.x_root), int(event.y_root), event.time)
                self._pos_manual = True
                return True
            except Exception as e:
                log.debug("begin_move_drag: %s", e)

        # Wayland layer-shell: arrasto manual pelas margins
        self._arrastando = True
        self._drag_off_x = event.x_root - self._pos_x
        self._drag_off_y = event.y_root - self._pos_y
        return True

    def _mostrar_menu_contexto(self, event):
        menu = Gtk.Menu()
        for rotulo, handler in (
            ("Configurações",    self._menu_configuracoes),
            ("Recarregar clima",  self._menu_recarregar_clima),
            ("Resetar posição",   self._menu_resetar_posicao),
            ("Sair",              self._menu_sair),
        ):
            item = Gtk.MenuItem(label=rotulo)
            item.connect("activate", handler)
            menu.append(item)
        menu.show_all()
        menu.attach_to_widget(self, None)
        menu.popup_at_pointer(event)
        self._menu_ativo = menu  # mantém referência viva até ser fechado

    def _menu_configuracoes(self, _item):
        if self._stack.get_visible_child_name() != "config":
            self._on_toggle_config(self)

    def _menu_recarregar_clima(self, _item):
        mod_clima.limpar_cache_localizacao()
        threading.Thread(target=self._bg_clima, daemon=True).start()

    def _menu_resetar_posicao(self, _item):
        try:
            (Path(__file__).parent / "config" / ".widget_pos").unlink(missing_ok=True)
        except Exception:
            pass
        self._pos_manual = False
        self._monitor_geo = self._ler_monitor_geo()
        geo = self._monitor_geo
        x = self._calcular_pos_x(geo)
        y = geo.y + (geo.height - self._altura_atual) // 2
        self._mover_para(x, y)

    def _menu_sair(self, _item):
        self._espectro.stop()
        Gtk.main_quit()

    def _durante_arrasto(self, widget, event):
        if not self._ls or not self._arrastando:
            return False
        if not (event.state & Gdk.ModifierType.BUTTON1_MASK):
            self._arrastando = False
            return False
        x = int(event.x_root - self._drag_off_x)
        y = int(event.y_root - self._drag_off_y)
        x, y = self._clamp_pos(x, y)
        self._pos_manual = True
        self._mover_para(x, y)
        return True

    def _fim_arrasto(self, widget, event):
        if event.button != 1:
            return False
        if self._ls and self._arrastando:
            self._arrastando = False
            self._pos_manual = True
            self._salvar_posicao()
            return True
        return False

    def _on_configure(self, _widget, event):
        """Atualiza posição após arrasto nativo X11."""
        if self._ls:
            return False
        if event.x != self._pos_x or event.y != self._pos_y:
            self._pos_x = int(event.x)
            self._pos_y = int(event.y)
            self._pos_manual = True
            # Debounce: grava 400ms após parar de mover
            if getattr(self, "_pos_save_id", 0):
                GLib.source_remove(self._pos_save_id)
            self._pos_save_id = GLib.timeout_add(400, self._salvar_posicao_debounce)
        return False

    def _salvar_posicao_debounce(self):
        self._pos_save_id = 0
        self._salvar_posicao()
        return False

    def _salvar_posicao(self):
        """Grava posição em arquivo fora do hot-reload (.py)."""
        arq = Path(__file__).parent / "config" / ".widget_pos"
        try:
            arq.write_text(f"{int(self._pos_x)} {int(self._pos_y)}\n", encoding="utf-8")
        except Exception as e:
            log.debug("salvar posição: %s", e)

    @staticmethod
    def _carregar_posicao_arquivo():
        arq = Path(__file__).parent / "config" / ".widget_pos"
        try:
            x_s, y_s = arq.read_text(encoding="utf-8").split()
            return int(x_s), int(y_s)
        except Exception:
            return -1, -1

    # ── Visualizador de espectro ──────────────────────────────────────────

    def _tick_espectro(self):
        if self.espectro_area.get_visible():
            self.espectro_area.set_levels(self._espectro.get_bars())
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
        # Memoriza wallpaper atual; se auto estiver ligado, reage a mudanças
        self._wall_path_atual = mod_wall.localizar_wallpaper()
        est = mod_wall.caminho_estado_cosmic()
        try:
            self._wall_mtime = est.stat().st_mtime if est.is_file() else None
        except Exception:
            self._wall_mtime = None
        GLib.timeout_add_seconds(4, self._verificar_wallpaper)

    def _verificar_wallpaper(self):
        if not ADAPTAR_WALLPAPER_AUTO:
            return True
        est = mod_wall.caminho_estado_cosmic()
        try:
            mtime = est.stat().st_mtime if est.is_file() else None
        except Exception:
            return True
        caminho = mod_wall.localizar_wallpaper()
        if self._wall_path_atual is None:
            self._wall_path_atual = caminho
            self._wall_mtime = mtime
            return True
        if mtime == self._wall_mtime and caminho == self._wall_path_atual:
            return True
        antigo = self._wall_path_atual
        self._wall_mtime = mtime
        self._wall_path_atual = caminho
        if caminho and caminho != antigo:
            log.info("wallpaper mudou → %s", caminho)
            threading.Thread(target=self._bg_adaptar_wallpaper_auto, daemon=True).start()
        return True

    def _bg_adaptar_wallpaper_auto(self):
        tema, info = mod_wall.adaptar_ao_wallpaper()
        if tema:
            GLib.idle_add(self._aplicar_tema_wallpaper_auto, tema, info)

    def _aplicar_tema_wallpaper_auto(self, tema, info):
        try:
            self._gravar_e_aplicar_tema(tema)
            log.info("cores adaptadas automaticamente de %s", info)
        except Exception as e:
            log.warning("auto wallpaper: %s", e)
        return False

    # ── Hot reload por mtime ────────────────────────────────────────────

    def _verificar_config(self):
        if any(p.stat().st_mtime != self._config_mtimes.get(p) for p in self._config_arquivos):
            log.info("configuração alterada — recarregando sem reiniciar")
            self._recarregar_config()
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

    def _atualizar_icone_clima(self, codigo):
        """Desenha ícone vetorial do clima (estilo README, sem emoji)."""
        try:
            if codigo is None:
                from weather_icons import SOL, renderizar
                pb = renderizar(SOL, tamanho=_px(36), cor=COR_TEXTO)
            else:
                pb = mod_clima.icone_pixbuf(int(codigo), tamanho=_px(36), cor=COR_TEXTO)
            self.img_icone_clima.set_from_pixbuf(pb)
            self._codigo_clima_atual = codigo
        except Exception as e:
            log.warning("ícone clima: %s", e)

    def _atualizar_previsao(self, previsao):
        for i, (lbl_dia, img, lbl_temp) in enumerate(self._previsao_widgets):
            if i < len(previsao):
                d = previsao[i]
                lbl_dia.set_text(str(d.get("dia", "")).upper())
                try:
                    img.set_from_pixbuf(
                        mod_clima.icone_pixbuf(
                            int(d.get("codigo", 113)), tamanho=_px(20), cor=COR_TEXTO_SECUNDARIO))
                except Exception as e:
                    log.debug("ícone previsão: %s", e)
                lbl_temp.set_text(f"{d.get('max_c', '--')}° / {d.get('min_c', '--')}°")
            else:
                lbl_dia.set_text("")
                img.clear()
                lbl_temp.set_text("")

    def _aplicar_clima(self, dados):
        if dados:
            self._atualizar_icone_clima(dados["codigo"])
            if UNIDADE_TEMPERATURA.strip().upper() in ("°F", "F"):
                temp = dados.get("temp_f")
                if temp is None:
                    temp = round(int(dados["temp"]) * 9 / 5 + 32)
                unidade = "°F"
            else:
                temp = dados.get("temp_c", dados["temp"])
                unidade = "°C"
            self.lbl_temperatura.set_text(f"  {temp}{unidade}")
            self.lbl_cidade.set_text(dados["cidade"])
            self.lbl_descricao.set_text(dados["descricao"])
            self.lbl_detalhe.set_text(
                FORMATO_VENTO_UMIDADE.format(vento=dados["vento_ms"], umidade=dados["umidade"])
            )
            self._atualizar_previsao(dados.get("previsao") or [])
            if NOTIFICAR_CHUVA_FORTE and not dados.get("cache"):
                try:
                    mod_clima.notificar_chuva_forte(dados)
                except Exception as e:
                    log.debug("notificar chuva: %s", e)
        else:
            self.lbl_cidade.set_text(TEXTO_SEM_CONEXAO)
            self.lbl_descricao.set_text("")
            self.lbl_detalhe.set_text("")
        GLib.idle_add(self._medir_altura_natural)
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

    def _on_spotify_prev(self, _widget):
        if mod_spotify.comando("Previous"):
            GLib.timeout_add(200, self._spotify_refresh_once)

    def _on_spotify_next(self, _widget):
        if mod_spotify.comando("Next"):
            GLib.timeout_add(200, self._spotify_refresh_once)

    def _on_spotify_play_pause(self, _widget):
        if mod_spotify.comando("PlayPause"):
            GLib.timeout_add(200, self._spotify_refresh_once)

    def _on_volume_changed(self, scale):
        if self._volume_syncing:
            return
        vol = scale.get_value() / 100.0
        threading.Thread(
            target=mod_spotify.definir_volume, args=(vol,), daemon=True).start()

    def _aplicar_spotify(self, dados):
        tocando = dados and dados["status"] in ("Playing", "Running")
        pausado = dados and dados["status"] == "Paused"

        spotify_aberto = bool(dados)
        for b in (self.btn_spotify_prev, self.btn_spotify_play, self.btn_spotify_next):
            b.set_habilitado(spotify_aberto)
        self.scale_volume.set_sensitive(spotify_aberto and dados.get("volume") is not None)
        if dados and dados.get("volume") is not None:
            self._volume_syncing = True
            try:
                self.scale_volume.set_value(max(0.0, min(100.0, float(dados["volume"]) * 100)))
            finally:
                self._volume_syncing = False
        if dados:
            self.btn_spotify_play.set_tipo("pause" if tocando else "play")
            self.btn_spotify_play.set_tooltip_text(
                TOOLTIP_SPOTIFY_PAUSE if tocando else TOOLTIP_SPOTIFY_PLAY)

        self.lbl_sem_musica.set_visible(not spotify_aberto)
        self.lbl_cabecalho_spotify.set_text(
            (TEXTO_PAUSADO if pausado else TEXTO_TOCANDO) if dados else "")

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
        pb = mod_spotify.carregar_capa(url, _px(TAMANHO_CAPA))
        GLib.idle_add(self._aplicar_capa, pb)

    def _aplicar_capa(self, pb):
        if pb:
            self.img_capa.set_from_pixbuf(pb)
        return False
