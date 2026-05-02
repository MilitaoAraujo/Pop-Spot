# Janela principal do widget — layout, arraste, redimensionamento e loops de atualização
# Main widget window — layout, drag, resize and update loops
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

from config import LARGURA, MARGEM_DIREITA, MARGEM_TOPO, TAMANHO_CAPA, BORDA_RESIZE, LARGURA_MINIMA, ALTURA_MINIMA
from config import ATUALIZAR_CLIMA_SEG, ATUALIZAR_SPOTIFY_SEG
from config import (
    ICONE_SPOTIFY, TEXTO_TOCANDO, TEXTO_PAUSADO, PREFIXO_PAUSADO, TEXTO_SEM_SPOTIFY,
    ICONE_SPOTIFY_ANTERIOR, ICONE_SPOTIFY_PROXIMO,
    ICONE_SPOTIFY_REPRODUZIR, ICONE_SPOTIFY_PAUSAR,
    TOOLTIP_SPOTIFY_ANTERIOR, TOOLTIP_SPOTIFY_PLAY, TOOLTIP_SPOTIFY_PAUSE, TOOLTIP_SPOTIFY_PROXIMO,
    ICONE_CLIMA_PADRAO, TEXTO_BUSCANDO_CLIMA, TEXTO_SEM_CONEXAO, FORMATO_VENTO_UMIDADE,
    UNIDADE_TEMPERATURA, DIAS_SEMANA, TEXTO_PROGRESSO_DIA,
)
from config import COR_DESTAQUE, COR_TEXTO, COR_BASE
from css     import gerar_css
import weather  as mod_clima
import spotify  as mod_spotify
from spectrum import AudioSpectrum

log = logging.getLogger("widget")

# Força locale português para nomes de dia/mês em strftime
for _loc in ("pt_BR.UTF-8", "pt_BR", "pt_PT.UTF-8", "pt_PT", ""):
    try:
        locale.setlocale(locale.LC_TIME, _loc)
        break
    except locale.Error:
        continue

def _parsear_cores_espectro():
    """Converte as 3 cores base do config para tuplas (r,g,b) usadas pelo Cairo."""
    def _hex(c):
        h = c.lstrip("#")
        return int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    return _hex(COR_BASE), _hex(COR_TEXTO), _hex(COR_DESTAQUE)


# Cursores do mouse para cada zona de arraste
_CURSORES_ZONA = {
    'N':  'n-resize',  'S':  's-resize',
    'E':  'e-resize',  'W':  'w-resize',
    'NE': 'ne-resize', 'NW': 'nw-resize',
    'SE': 'se-resize', 'SW': 'sw-resize',
    'mover': 'grab',
}


class WidgetDesktop(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._url_capa_atual   = None
        self._ls               = None   # referência ao GtkLayerShell quando ativo
        self._pos_x            = 0     # posição X atual do widget na tela
        self._pos_y            = 0     # posição Y atual do widget na tela
        self._spotify_ocupado  = False  # evita threads simultâneas de busca do Spotify

        # Estado de arraste (mover ou redimensionar)
        self._drag_ativo  = False
        self._drag_tipo   = None  # 'mover' | 'N' | 'S' | 'E' | 'W' | 'NE' | etc.
        self._drag_ini_x  = 0    # posição X do mouse (local à superfície) ao iniciar o arraste
        self._drag_ini_y  = 0    # posição Y do mouse (local à superfície) ao iniciar o arraste
        self._drag_ini_w  = 0    # largura do widget ao iniciar o arraste
        self._drag_ini_h  = 0    # altura do widget ao iniciar o arraste
        self._drag_ini_px = 0    # posição X do widget ao iniciar o arraste
        self._drag_ini_py = 0    # posição Y do widget ao iniciar o arraste
        self._altura_atual   = 800
        self._espectro       = AudioSpectrum()
        self._cal_dia        = -1
        self._cores_espectro = _parsear_cores_espectro()

        # Hot reload — rastreia mtimes dos arquivos de config
        # Hot reload — tracks mtimes of config files
        _cfg = Path(__file__).parent / "config"
        self._config_arquivos = [
            p for p in _cfg.glob("*.py") if not p.name.startswith("_")
        ]
        self._config_mtimes = {p: p.stat().st_mtime for p in self._config_arquivos}

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
        self.set_decorated(False)  # sem barra de título
        self.set_resizable(True)   # necessário para self.resize() funcionar

        # Transparência: define visual RGBA para cantos arredondados funcionarem
        tela   = self.get_screen()
        visual = tela.get_rgba_visual()
        if visual and tela.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.connect("draw", self._desenhar_fundo)
        self.connect("window-state-event", self._bloquear_maximizar)

        # Calcula posição inicial: canto superior direito da tela
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geo     = monitor.get_geometry()
        self._pos_x = geo.x + geo.width - LARGURA - MARGEM_DIREITA
        self._pos_y = geo.y + MARGEM_TOPO

        # Tenta usar gtk-layer-shell (Wayland) para fixar no desktop de verdade
        if self._ativar_layer_shell():
            log.warning("gtk-layer-shell ativo — widget fixo no desktop (Wayland)")
        else:
            # Fallback para X11 ou Wayland sem layer-shell instalado
            self.set_keep_below(True)
            self.set_skip_taskbar_hint(True)
            self.set_skip_pager_hint(True)
            self.stick()
            self.move(self._pos_x, self._pos_y)

    def _desenhar_fundo(self, _widget, cr):
        """Limpa o fundo da janela para transparente.
        IMPORTANTE: deve retornar False para o GTK continuar desenhando os filhos."""
        cr.set_source_rgba(0, 0, 0, 0)
        try:
            import cairo
            cr.set_operator(cairo.OPERATOR_SOURCE)
        except ImportError:
            cr.set_operator(1)  # cairo.OPERATOR_SOURCE
        cr.paint()
        return False

    def _bloquear_maximizar(self, _widget, evento):
        """Reverte imediatamente qualquer tentativa de maximizar ou ir a tela cheia."""
        estado = evento.new_window_state
        if estado & Gdk.WindowState.MAXIMIZED:
            self.unmaximize()
        if estado & Gdk.WindowState.FULLSCREEN:
            self.unfullscreen()

    def _ativar_layer_shell(self):
        """Configura a janela como widget de desktop via Wayland Layer Shell.
        Posicionamento livre via margens TOP+LEFT — permite mover para qualquer lugar.
        Retorna True se conseguiu, False caso a biblioteca não esteja instalada."""
        try:
            gi.require_version("GtkLayerShell", "0.1")
            from gi.repository import GtkLayerShell

            self._ls = GtkLayerShell
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP,  True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP,  max(0, self._pos_y))
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, max(0, self._pos_x))
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
            return True
        except Exception:
            self._ls = None
            return False

    def _inicializar_altura(self, _widget):
        """Agenda medição no próximo idle — garante que CSS e layout estão prontos."""
        GLib.idle_add(self._medir_altura_natural)

    def _medir_altura_natural(self):
        """Mede a altura natural real e aplica como tamanho inicial do widget."""
        _min, nat = self._raiz.get_preferred_height()
        h = max(ALTURA_MINIMA, nat + 20)
        self._altura_atual = h
        self._raiz.set_size_request(LARGURA, nat)
        self.queue_resize()
        return False

    # ── Sobreescrita do GTK para controle real de altura no Wayland ──────────

    def do_get_preferred_height(self):
        """Informa ao GTK/Wayland a altura exata da janela."""
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
        """Move o widget para a posição (x, y)."""
        self._pos_x = x
        self._pos_y = y
        if self._ls:
            self._ls.set_margin(self, self._ls.Edge.LEFT, max(0, x))
            self._ls.set_margin(self, self._ls.Edge.TOP,  max(0, y))
        else:
            self.move(x, y)

    # ── Construção da interface ───────────────────────────────────────────

    def _construir_ui(self):
        # EventBox cobre toda a janela — detecta zona do clique e decide mover ou redimensionar.
        # above_child=False: filhos (ex.: botões Spotify) recebem o clique primeiro; o arraste
        # continua funcionando nas áreas sem janela própria ou quando o evento propaga.
        caixa_evento = Gtk.EventBox()
        caixa_evento.set_above_child(False)
        caixa_evento.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK   |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )
        caixa_evento.connect("button-press-event",   self._drag_press)
        caixa_evento.connect("motion-notify-event",  self._drag_motion)
        caixa_evento.connect("button-release-event", self._drag_release)

        raiz = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        raiz.get_style_context().add_class("raiz")
        raiz.set_size_request(LARGURA, -1)
        self._raiz = raiz

        # ── Relógio ──────────────────────────────────────────────────────
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

        # ── Clima ────────────────────────────────────────────────────────
        caixa_clima = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        linha_temp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.lbl_icone_clima = self._rotulo("iconeClima",       ICONE_CLIMA_PADRAO, Gtk.Align.START)
        self.lbl_temperatura = self._rotulo("temperaturaClima", "--°C",         Gtk.Align.START)
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

        # ── Spotify ──────────────────────────────────────────────────────
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

        # Controles MPRIS: anterior, reproduzir/pausar, próxima
        linha_ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        linha_ctrl.set_halign(Gtk.Align.START)
        self.btn_spotify_prev = self._botao_spotify(
            ICONE_SPOTIFY_ANTERIOR, TOOLTIP_SPOTIFY_ANTERIOR)
        self.btn_spotify_prev.connect("clicked", self._on_spotify_prev)
        self.btn_spotify_play = self._botao_spotify(
            ICONE_SPOTIFY_REPRODUZIR, TOOLTIP_SPOTIFY_PLAY)
        self.btn_spotify_play.connect("clicked", self._on_spotify_play_pause)
        self.btn_spotify_next = self._botao_spotify(
            ICONE_SPOTIFY_PROXIMO, TOOLTIP_SPOTIFY_PROXIMO)
        self.btn_spotify_next.connect("clicked", self._on_spotify_next)
        for b in (self.btn_spotify_prev, self.btn_spotify_play, self.btn_spotify_next):
            linha_ctrl.pack_start(b, False, False, 0)
        caixa_spotify.pack_start(linha_ctrl, False, False, 8)

        self.lbl_titulo     = self._rotulo("tituloMusica",  "", Gtk.Align.START, reticencias=True)
        self.lbl_artista    = self._rotulo("artistaMusica", "", Gtk.Align.START, reticencias=True)
        self.lbl_album      = self._rotulo("albumMusica",   "", Gtk.Align.START, reticencias=True)
        self.lbl_sem_musica = self._rotulo("semMusica", TEXTO_SEM_SPOTIFY, Gtk.Align.START)

        # Caixa de texto (título, artista, álbum)
        caixa_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for w in (self.lbl_titulo, self.lbl_artista, self.lbl_album):
            caixa_info.pack_start(w, False, False, 0)

        # Visualizador de espectro — sempre visível, linha reta quando silencioso
        self.espectro_area = Gtk.DrawingArea()
        self.espectro_area.set_size_request(95, 55)
        self.espectro_area.set_valign(Gtk.Align.CENTER)
        self.espectro_area.connect("draw", self._desenhar_espectro)

        linha_musica = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        linha_musica.pack_start(caixa_info,        True,  True,  0)
        linha_musica.pack_start(self.espectro_area, False, False, 0)

        caixa_spotify.pack_start(linha_musica,      False, False, 0)
        caixa_spotify.pack_start(self.lbl_sem_musica, False, False, 0)

        raiz.pack_start(caixa_spotify, False, False, 0)

        self.connect("map", self._inicializar_altura)
        caixa_evento.add(raiz)
        self.add(caixa_evento)

    # ── Painel direito do relógio (progresso + calendário) ────────────────

    def _construir_painel_dir(self):
        painel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        painel.set_valign(Gtk.Align.CENTER)
        painel.set_size_request(95, -1)

        # Linha com "Progresso do dia" + porcentagem lado a lado
        linha_prog = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        linha_prog.set_halign(Gtk.Align.END)
        if TEXTO_PROGRESSO_DIA:
            lbl_prog_label = self._rotulo("progLabel", TEXTO_PROGRESSO_DIA, Gtk.Align.END)
            linha_prog.pack_start(lbl_prog_label, False, False, 0)
        self.lbl_prog_pct = self._rotulo("progPct", "0%", Gtk.Align.END)
        linha_prog.pack_start(self.lbl_prog_pct, False, False, 0)
        painel.pack_start(linha_prog, False, False, 0)

        # Barra de progresso
        self.barra_dia = Gtk.ProgressBar()
        self.barra_dia.get_style_context().add_class("barDia")
        self.barra_dia.set_show_text(False)
        self.barra_dia.set_fraction(0.0)
        painel.pack_start(self.barra_dia, False, False, 0)

        # Grid do mini calendário
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

        # Cabeçalhos: Seg → Dom
        for col, h in enumerate(DIAS_SEMANA):
            lbl = Gtk.Label(label=h)
            lbl.get_style_context().add_class("calHdr")
            self._cal_grid.attach(lbl, col, 0, 1, 1)

        # Dias do mês (semanas começam na segunda)
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

    def _botao_spotify(self, texto: str, tooltip: str) -> Gtk.Button:
        b = Gtk.Button.new_with_label(texto)
        b.get_style_context().add_class("btnSpotify")
        b.set_tooltip_text(tooltip)
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_sensitive(False)
        return b

    def _separador(self):
        s = Gtk.EventBox()
        s.get_style_context().add_class("sep")
        s.set_hexpand(True)
        return s

    # ── Sistema de arraste (mover + redimensionar por qualquer borda/canto) ──

    def _zona_do_clique(self, x, y):
        """Detecta em qual zona do widget o clique ocorreu."""
        w = self.get_allocated_width()
        h = self._altura_atual if self._altura_atual > 0 else self.get_allocated_height()
        g = BORDA_RESIZE
        esq  = x < g
        dir_ = x > w - g
        top  = y < g
        bot  = y > h - g
        if esq and top:  return 'NW'
        if dir_ and top: return 'NE'
        if esq and bot:  return 'SW'
        if dir_ and bot: return 'SE'
        if top:  return 'N'
        if bot:  return 'S'
        if esq:  return 'W'
        if dir_: return 'E'
        return 'mover'

    def _drag_press(self, widget, event):
        """Registra início do arraste e determina a ação."""
        if event.button != 1:
            return
        zona = self._zona_do_clique(event.x, event.y)
        self._drag_ativo  = True
        self._drag_tipo   = zona
        # No Wayland layer-shell o GDK não atualiza a posição interna da superfície
        # quando mudamos as margens, então event.x_root vira coordenada absoluta estável.
        # No X11, event.x_root também é coordenada absoluta. Ambos funcionam igual aqui.
        # O problema de startup era que event.x_root retornava 0 no primeiro clique após
        # o autostart — event.x (local à superfície) é sempre confiável.
        # Como no Wayland layer-shell event.x ≈ cursor_abs (surface_x=0 no GDK),
        # event.x e event.x_root são equivalentes; usamos event.x para evitar o bug de startup.
        if self._ls:
            self._drag_ini_x  = event.x
            self._drag_ini_y  = event.y
        else:
            self._drag_ini_x  = event.x_root
            self._drag_ini_y  = event.y_root
        self._drag_ini_w  = self.get_allocated_width()
        self._drag_ini_h  = self._altura_atual if self._altura_atual > 0 else self.get_allocated_height()
        self._drag_ini_px = self._pos_x
        self._drag_ini_py = self._pos_y
        widget.grab_add()

    def _drag_motion(self, _widget, event):
        """Move o widget ou redimensiona conforme a zona onde o arraste começou."""
        if not self._drag_ativo:
            zona  = self._zona_do_clique(event.x, event.y)
            nome  = _CURSORES_ZONA.get(zona, 'default')
            gdk_w = self.get_window()
            if gdk_w:
                gdk_w.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), nome))
            return

        if self._ls:
            dx = event.x       - self._drag_ini_x
            dy = event.y       - self._drag_ini_y
        else:
            dx = event.x_root  - self._drag_ini_x
            dy = event.y_root  - self._drag_ini_y
        t  = self._drag_tipo

        new_w = self._drag_ini_w
        new_h = self._drag_ini_h
        new_x = self._drag_ini_px
        new_y = self._drag_ini_py

        if t == 'mover':
            new_x = self._drag_ini_px + int(dx)
            new_y = self._drag_ini_py + int(dy)
        else:
            if 'E' in t:
                new_w = max(LARGURA_MINIMA, self._drag_ini_w + int(dx))
            if 'W' in t:
                dw    = min(int(dx), self._drag_ini_w - LARGURA_MINIMA)
                new_w = self._drag_ini_w - dw
                new_x = self._drag_ini_px + dw
            if 'S' in t:
                new_h = max(ALTURA_MINIMA, self._drag_ini_h + int(dy))
            if 'N' in t:
                dh    = min(int(dy), self._drag_ini_h - ALTURA_MINIMA)
                new_h = self._drag_ini_h - dh
                new_y = self._drag_ini_py + dh

        if new_w != self._drag_ini_w or new_h != self._drag_ini_h:
            self._raiz.set_size_request(new_w, self._raiz.get_size_request()[1])
            self._altura_atual = max(ALTURA_MINIMA, new_h)
            self.queue_resize()
        if new_x != self._pos_x or new_y != self._pos_y:
            self._mover_para(new_x, new_y)

    def _drag_release(self, widget, event):
        """Finaliza o arraste ao soltar o botão do mouse."""
        if event.button == 1:
            self._drag_ativo = False
            self._drag_tipo  = None
            widget.grab_remove()
            gdk_w = self.get_window()
            if gdk_w:
                gdk_w.set_cursor(None)

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

        base = h - 0.75  # linha base na parte inferior da área

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
            bar_h = max(1.5, val * h)  # mínimo 1.5px para as barras ficarem na base
            x     = i * (bar_w + gap)
            y     = h - bar_h

            # Gradiente de cor: texto apagado → texto → destaque
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
        GLib.timeout_add(67, self._tick_espectro)           # ~15fps
        GLib.timeout_add(1500, self._verificar_config)     # hot reload

    # ── Hot reload ───────────────────────────────────────────────────────

    def _verificar_config(self):
        alterado = any(
            p.stat().st_mtime != self._config_mtimes[p]
            for p in self._config_arquivos
        )
        if alterado:
            log.warning("Configuração alterada — reiniciando / Config changed — restarting")
            self._espectro.stop()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        return True

    # ── Relógio ───────────────────────────────────────────────────────────

    def _tick_relogio(self):
        agora = datetime.datetime.now()
        self.lbl_hora.set_text(agora.strftime("%H"))
        self.lbl_minuto.set_text(agora.strftime("%M"))
        self.lbl_diasem.set_text(agora.strftime("%A").upper())
        self.lbl_data.set_text(agora.strftime("%d / %B / %Y").upper())

        # Progresso do dia
        seg = agora.hour * 3600 + agora.minute * 60 + agora.second
        prog = seg / 86400
        self.lbl_prog_pct.set_text(f"{int(prog * 100)}%")
        self.barra_dia.set_fraction(prog)

        # Calendário — reconstrói só quando o dia muda
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
                FORMATO_VENTO_UMIDADE.format(vento=dados['vento_ms'], umidade=dados['umidade'])
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

    def _on_spotify_prev(self, _btn):
        if mod_spotify.comando("Previous"):
            GLib.timeout_add(200, self._spotify_refresh_once)

    def _on_spotify_next(self, _btn):
        if mod_spotify.comando("Next"):
            GLib.timeout_add(200, self._spotify_refresh_once)

    def _on_spotify_play_pause(self, _btn):
        if mod_spotify.comando("PlayPause"):
            GLib.timeout_add(200, self._spotify_refresh_once)

    def _aplicar_spotify(self, dados):
        tocando = dados and dados["status"] in ("Playing", "Running")
        pausado = dados and dados["status"] == "Paused"

        ativo = bool(dados)
        for b in (self.btn_spotify_prev, self.btn_spotify_play, self.btn_spotify_next):
            b.set_sensitive(ativo)
        if dados:
            self.btn_spotify_play.set_label(
                ICONE_SPOTIFY_PAUSAR if tocando else ICONE_SPOTIFY_REPRODUZIR)
            self.btn_spotify_play.set_tooltip_text(
                TOOLTIP_SPOTIFY_PAUSE if tocando else TOOLTIP_SPOTIFY_PLAY)

        self.lbl_sem_musica.set_visible(not dados)
        if dados:
            self.lbl_cabecalho_spotify.set_text(TEXTO_PAUSADO if pausado else TEXTO_TOCANDO)

        if tocando or pausado:
            prefixo = PREFIXO_PAUSADO if pausado else ""
            self.lbl_titulo.set_text(prefixo + dados["titulo"])
            self.lbl_artista.set_text(dados["artista"])
            self.lbl_album.set_text(dados["album"])
            capa = dados["capa"]
            if capa and capa != self._url_capa_atual:
                self._url_capa_atual = capa
                threading.Thread(
                    target=self._bg_capa, args=(capa,), daemon=True
                ).start()
        else:
            self.lbl_titulo.set_text("")
            self.lbl_artista.set_text("")
            self.lbl_album.set_text("")
            self.img_capa.clear()
            self._url_capa_atual = None
        return False

    def _bg_capa(self, url):
        pb = mod_spotify.carregar_capa(url, TAMANHO_CAPA)
        GLib.idle_add(self._aplicar_capa, pb)

    def _aplicar_capa(self, pb):
        if pb:
            self.img_capa.set_from_pixbuf(pb)
        return False
