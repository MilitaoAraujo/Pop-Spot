"""No Linux/COSMIC: UI Qt desenhada dentro de uma janela GTK + layer-shell.

O Qt pip não tem plugin de layer-shell; sem isso o COSMIC trata a janela
como aplicativo (borda + dock). O GTK já sabe prender na área de trabalho.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def _usar_gi_do_sistema() -> None:
    """O venv tem o PySide6; o GTK/gi vem dos pacotes apt."""
    for p in (
        f"/usr/lib/python{sys.version_info.major}.{sys.version_info.minor}/dist-packages",
        "/usr/lib/python3/dist-packages",
    ):
        if Path(p).is_dir() and p not in sys.path:
            sys.path.append(p)


_usar_gi_do_sistema()
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

from config import LADO, MARGEM_DIREITA, POS_X, POS_Y, VERSAO
from config.i18n import t

log = logging.getLogger("popspot.win.host")

_RAIZ = Path(__file__).resolve().parent.parent
_POS_ARQ = _RAIZ / "config" / ".widget_pos"


class HostLinux(Gtk.Window):
    def __init__(self, qt_widget):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._qt = qt_widget
        self._ls = None
        self._pos_x = 0
        self._pos_y = 0
        self._pos_manual = False
        self._arrastando = False
        self._drag_off_x = 0.0
        self._drag_off_y = 0.0
        self._buf = b""
        self._cairo_data = None
        self._surf = None
        self._req = (0, 0)
        self._pintando = False
        self.set_title("Pop Spot")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_accept_focus(False)
        self.set_app_paintable(True)
        self._ativar_layer_shell()
        self._montar()
        self.connect("destroy", lambda *_: self._sair())
        GLib.timeout_add(50, self._tick)
        GLib.idle_add(self._posicionar)

    def _ativar_layer_shell(self) -> bool:
        try:
            gi.require_version("GtkLayerShell", "0.1")
            from gi.repository import GtkLayerShell
            self._ls = GtkLayerShell
            GtkLayerShell.init_for_window(self)
            if hasattr(GtkLayerShell, "set_namespace"):
                GtkLayerShell.set_namespace(self, "pop-spot-qt")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
            if hasattr(GtkLayerShell, "set_exclusive_zone"):
                GtkLayerShell.set_exclusive_zone(self, -1)
            return True
        except Exception as e:
            log.warning("layer-shell: %s", e)
            self._ls = None
            self.set_keep_below(True)
            self.set_skip_taskbar_hint(True)
            self.set_skip_pager_hint(True)
            return False

    def _montar(self):
        self._img = Gtk.Image()
        caixa = Gtk.EventBox()
        caixa.set_visible_window(False)
        caixa.set_can_focus(False)
        caixa.add(self._img)
        caixa.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON1_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        caixa.connect("button-press-event", self._on_press)
        caixa.connect("button-release-event", self._on_release)
        caixa.connect("motion-notify-event", self._on_motion)
        caixa.connect("scroll-event", self._on_scroll)
        self._fixed = Gtk.Fixed()
        self._caixa = caixa
        self._fixed.put(caixa, 0, 0)
        self.add(self._fixed)
        masc = (
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON1_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.SMOOTH_SCROLL_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
        )
        self.add_events(masc)
        self.connect("button-press-event", self._on_press)
        self.connect("button-release-event", self._on_release)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("scroll-event", self._on_scroll)
        self.connect("key-press-event", self._on_key)
        self._qt._pagina_cfg.pedir_cor.connect(self._cor_gtk)
        self._qt_grab = None
        self._qt_edit = None
        self._kb_aberto = None
        self._gtk_edits = {}
        self._css_edits = None
        self._css_edits_sig = None
        self._syncing_edit = False

    def _tick(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        self._teclado_se_config()
        self._pintar()
        self._sync_edits_gtk()
        return True

    def _pintar(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QImage, QPainter

        if self._pintando:
            return
        lay = self._qt.layout()
        if lay is not None:
            lay.activate()
        w, h = self._qt.width(), self._qt.height()
        if w < 8 or h < 8:
            return
        self._pintando = True
        try:
            scale = max(1, int(self.get_scale_factor() or 1))
            iw, ih = w * scale, h * scale
            img = QImage(iw, ih, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(0)
            img.setDevicePixelRatio(float(scale))
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self._qt.render(p, QPoint())
            p.end()
            if not self._aplicar_superficie(img, scale):
                self._aplicar_pixbuf(img, w, h, scale)
            self._img.set_size_request(w, h)
            self._caixa.set_size_request(w, h)
            self._fixed.set_size_request(w, h)
            self._aplicar_input_cheia(w, h)
            if (w, h) != self._req:
                self.set_size_request(w, h)
                self.resize(w, h)
                self.queue_resize()
                self._req = (w, h)
        finally:
            self._pintando = False

    def _aplicar_input_cheia(self, w: int, h: int) -> None:
        """Wayland só entrega clique em pixel opaco; o widget inteiro deve arrastar."""
        gdk_win = self.get_window()
        if gdk_win is None or w < 1 or h < 1:
            return
        try:
            import cairo
            region = cairo.Region(cairo.RectangleInt(0, 0, int(w), int(h)))
            gdk_win.input_shape_combine_region(region, 0, 0)
        except Exception:
            pass

    def _aplicar_superficie(self, img, scale: int) -> bool:
        try:
            import cairo
            self._cairo_data = bytearray(img.constBits())
            surf = cairo.ImageSurface.create_for_data(
                self._cairo_data,
                cairo.FORMAT_ARGB32,
                img.width(),
                img.height(),
                img.bytesPerLine(),
            )
            surf.set_device_scale(scale, scale)
            self._surf = surf
            self._img.set_from_surface(surf)
            return True
        except Exception:
            return False

    def _aplicar_pixbuf(self, img, w: int, h: int, scale: int) -> None:
        from PySide6.QtGui import QImage
        rgba = img.convertToFormat(QImage.Format.Format_RGBA8888)
        self._buf = bytes(rgba.constBits())
        pb = GdkPixbuf.Pixbuf.new_from_data(
            self._buf,
            GdkPixbuf.Colorspace.RGB,
            True,
            8,
            rgba.width(),
            rgba.height(),
            rgba.bytesPerLine(),
        )
        if scale > 1:
            pb = pb.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
        self._img.set_from_pixbuf(pb)

    def _teclado_se_config(self):
        aberto = self._qt._stack.currentIndex() == 1
        if self._ls is not None:
            try:
                camada = (
                    self._ls.Layer.TOP if aberto else self._ls.Layer.BOTTOM
                )
                self._ls.set_layer(self, camada)
                modo = (
                    self._ls.KeyboardMode.EXCLUSIVE if aberto
                    else self._ls.KeyboardMode.NONE
                )
                self._ls.set_keyboard_mode(self, modo)
            except Exception:
                pass
        self.set_accept_focus(aberto)
        self.set_can_focus(aberto)
        if aberto != self._kb_aberto:
            self._kb_aberto = aberto
            if aberto:
                GLib.idle_add(self._focar_host)
            else:
                self._marcar_edit(None)
                self._esconder_edits_gtk()

    def _focar_host(self):
        try:
            self.grab_focus()
            gdk_win = self.get_window()
            if gdk_win is not None:
                gdk_win.focus(Gdk.CURRENT_TIME)
        except Exception:
            pass
        return False

    def _marcar_edit(self, edit):
        antigo = getattr(self, "_qt_edit", None)
        if antigo is not None and antigo is not edit:
            try:
                antigo.setProperty("hostFocus", False)
                antigo.style().unpolish(antigo)
                antigo.style().polish(antigo)
            except Exception:
                pass
        self._qt_edit = edit
        if edit is None:
            return
        from PySide6.QtCore import Qt as QtCore
        try:
            edit.setProperty("hostFocus", True)
            edit.style().unpolish(edit)
            edit.style().polish(edit)
            edit.setFocus(QtCore.FocusReason.MouseFocusReason)
            edit.setCursorPosition(len(edit.text() or ""))
        except Exception:
            pass

    def _css_provider_edits(self):
        from config import COR_SUPERFICIE, COR_TEXTO, COR_SEPARADOR, COR_DESTAQUE
        from win.scale import px
        sig = (COR_SUPERFICIE, COR_TEXTO, COR_SEPARADOR, COR_DESTAQUE, px(8))
        if self._css_edits is not None and self._css_edits_sig == sig:
            return self._css_edits
        css = f"""
        entry.popspot-edit {{
            background-color: {COR_SUPERFICIE};
            color: {COR_TEXTO};
            border: 1px solid {COR_SEPARADOR};
            border-radius: {px(8)}px;
            padding: {px(4)}px {px(8)}px;
            caret-color: {COR_DESTAQUE};
            min-height: {px(26)}px;
        }}
        entry.popspot-edit:focus {{
            border-color: {COR_DESTAQUE};
        }}
        """.encode()
        prov = Gtk.CssProvider()
        try:
            prov.load_from_data(css)
        except TypeError:
            prov.load_from_data(css.decode())
        self._css_edits = prov
        self._css_edits_sig = sig
        return prov

    def _rect_edit(self, w):
        from PySide6.QtCore import QPoint, QRect, QSize
        from PySide6.QtWidgets import QAbstractScrollArea
        canto = w.mapTo(self._qt, QPoint(0, 0))
        sz = w.size()
        if sz.width() < 8 or sz.height() < 8:
            sh = w.sizeHint()
            sz = QSize(max(sz.width(), sh.width(), 80), max(sz.height(), sh.height(), 28))
        r = QRect(canto, sz)
        parent = w.parentWidget()
        while parent is not None and parent is not self._qt:
            if isinstance(parent, QAbstractScrollArea):
                vp = parent.viewport()
                vc = vp.mapTo(self._qt, QPoint(0, 0))
                r = r.intersected(QRect(vc, vp.size()))
                break
            parent = parent.parentWidget()
        return r.intersected(QRect(0, 0, self._qt.width(), self._qt.height()))

    def _criar_entry_gtk(self, qedit):
        ge = Gtk.Entry()
        ge.set_has_frame(True)
        ge.get_style_context().add_class("popspot-edit")
        ge.set_can_focus(True)
        ge.get_style_context().add_provider(
            self._css_provider_edits(), Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        ge._pop_css_sig = self._css_edits_sig
        if qedit.objectName() == "entryHex":
            ge.set_max_length(7)
            ge.set_width_chars(7)
        ph = qedit.placeholderText()
        if ph:
            ge.set_placeholder_text(ph)
        ge.set_text(qedit.text() or "")
        ge.connect("changed", self._on_gtk_edit_changed, qedit)
        ge.connect("button-press-event", self._on_gtk_edit_press)
        ge.connect("focus-in-event", self._on_gtk_edit_focus, qedit)
        self._fixed.put(ge, 0, 0)
        return ge

    def _on_gtk_edit_changed(self, ge, qedit):
        if self._syncing_edit:
            return
        txt = ge.get_text()
        if qedit.text() != txt:
            qedit.setText(txt)
            self._pintar()

    def _on_gtk_edit_press(self, ge, _event):
        self._teclado_se_config()
        ge.grab_focus()
        return False

    def _on_gtk_edit_focus(self, _ge, _event, qedit):
        self._marcar_edit(qedit)
        self._teclado_se_config()
        return False

    def _esconder_edits_gtk(self):
        for ge in self._gtk_edits.values():
            ge.hide()

    def _sync_edits_gtk(self):
        from PySide6.QtWidgets import QLineEdit
        aberto = self._qt._stack.currentIndex() == 1
        if not aberto:
            self._esconder_edits_gtk()
            return
        self._css_provider_edits()
        vivos = set()
        for w in self._qt.findChildren(QLineEdit):
            if w.isHidden() or not w.isEnabled():
                continue
            r = self._rect_edit(w)
            if r.width() < 24 or r.height() < 16:
                ge = self._gtk_edits.get(w)
                if ge is not None:
                    ge.hide()
                continue
            vivos.add(w)
            ge = self._gtk_edits.get(w)
            if ge is None:
                ge = self._criar_entry_gtk(w)
                self._gtk_edits[w] = ge
            elif getattr(ge, "_pop_css_sig", None) != self._css_edits_sig:
                ge.get_style_context().add_provider(
                    self._css_provider_edits(), Gtk.STYLE_PROVIDER_PRIORITY_USER
                )
                ge._pop_css_sig = self._css_edits_sig
            x, y, rw, rh = int(r.x()), int(r.y()), int(r.width()), int(r.height())
            geom = getattr(ge, "_pop_geom", None)
            if geom != (x, y, rw, rh):
                self._fixed.move(ge, x, y)
                ge.set_size_request(rw, rh)
                ge._pop_geom = (x, y, rw, rh)
            ph = w.placeholderText()
            if ph and ge.get_placeholder_text() != ph:
                ge.set_placeholder_text(ph)
            if not ge.has_focus():
                self._syncing_edit = True
                try:
                    if ge.get_text() != (w.text() or ""):
                        ge.set_text(w.text() or "")
                finally:
                    self._syncing_edit = False
            if not ge.get_visible():
                ge.show()
        for w, ge in self._gtk_edits.items():
            if w not in vivos:
                ge.hide()

    def _map_xy(self, event):
        return int(event.x), int(event.y)

    def _widget_mostrado(self, w) -> bool:
        if w is None or not w.isEnabled() or w.isHidden():
            return False
        p = w.parentWidget()
        while p is not None and p is not self._qt:
            if p.isHidden():
                return False
            p = p.parentWidget()
        return True

    def _rect_hit(self, w):
        from PySide6.QtCore import QPoint, QRect
        from PySide6.QtWidgets import QAbstractScrollArea
        r = QRect(w.mapTo(self._qt, QPoint(0, 0)), w.size())
        p = w.parentWidget()
        while p is not None and p is not self._qt:
            if isinstance(p, QAbstractScrollArea):
                vp = p.viewport()
                r = r.intersected(QRect(vp.mapTo(self._qt, QPoint(0, 0)), vp.size()))
                break
            p = p.parentWidget()
        return r.intersected(QRect(0, 0, self._qt.width(), self._qt.height()))

    def _alvo_interativo(self, x: int, y: int):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import (
            QAbstractButton, QAbstractSlider, QLineEdit, QListWidget, QScrollBar, QSlider,
        )
        pt = QPoint(int(x), int(y))
        hits = []
        for cls, extra in (
            (QLineEdit, 2),
            (QListWidget, 2),
            (QSlider, 4),
            (QScrollBar, 2),
            (QAbstractButton, 0),
        ):
            for w in self._qt.findChildren(cls):
                if not self._widget_mostrado(w):
                    continue
                if isinstance(w, QAbstractSlider) and cls is QAbstractButton:
                    continue
                r = self._rect_hit(w).adjusted(-extra, -extra, extra, extra)
                if r.contains(pt) and r.width() > 2 and r.height() > 2:
                    hits.append((r.width() * r.height(), w))
        if hits:
            hits.sort(key=lambda t: t[0])
            return hits[0][1]
        return None

    def _slider_valor(self, slider, x: int, y: int) -> None:
        from PySide6.QtCore import QPoint
        pt = slider.mapFrom(self._qt, QPoint(int(x), int(y)))
        pad = 8
        span = max(1, slider.width() - 2 * pad)
        ratio = max(0.0, min(1.0, (pt.x() - pad) / span))
        if slider.invertedAppearance():
            ratio = 1.0 - ratio
        mn, mx = slider.minimum(), slider.maximum()
        slider.setValue(int(round(mn + ratio * (mx - mn))))

    def _enviar_mouse(self, alvo, x, y, event, tipo):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtWidgets import QApplication
        pt = alvo.mapFrom(self._qt, QPoint(int(x), int(y)))
        btn_n = int(getattr(event, "button", 0) or 0)
        if btn_n == 0 and (event.state & Gdk.ModifierType.BUTTON1_MASK):
            btn_n = 1
        botoes = Qt.MouseButton.LeftButton if btn_n == 1 else Qt.MouseButton.NoButton
        ev = QMouseEvent(
            tipo,
            QPointF(pt),
            QPointF(pt),
            Qt.MouseButton.LeftButton if btn_n == 1 else Qt.MouseButton.NoButton,
            botoes,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(alvo, ev)

    def _on_press(self, _w, event):
        try:
            return self._on_press_ok(event)
        except Exception:
            log.exception("press")
            return False

    def _on_press_ok(self, event):
        if event.button == 3:
            self._menu(event)
            return True
        if event.button != 1:
            return False
        from PySide6.QtCore import QEvent, QPoint
        from PySide6.QtWidgets import QAbstractButton, QAbstractSlider, QLineEdit, QListWidget, QSlider

        x, y = self._map_xy(event)
        alvo = self._alvo_interativo(x, y)
        if alvo is None:
            self._arrastando = True
            self._drag_off_x = event.x_root - self._pos_x
            self._drag_off_y = event.y_root - self._pos_y
            return True
        if isinstance(alvo, QSlider):
            self._slider_valor(alvo, x, y)
            self._qt_grab = alvo
            self._qt._slider_ativo = alvo
            self._pintar()
            return True
        if isinstance(alvo, QAbstractButton) and not isinstance(alvo, QAbstractSlider):
            alvo.click()
            self._pintar()
            return True
        if isinstance(alvo, QListWidget):
            pt = alvo.mapFrom(self._qt, QPoint(x, y))
            it = alvo.itemAt(pt)
            if it is not None:
                alvo.setCurrentItem(it)
                alvo.itemClicked.emit(it)
            self._pintar()
            return True
        if isinstance(alvo, QLineEdit):
            self._marcar_edit(alvo)
            self._teclado_se_config()
            ge = self._gtk_edits.get(alvo)
            if ge is not None:
                ge.grab_focus()
            else:
                self._focar_host()
            self._pintar()
            return True
        if isinstance(alvo, QAbstractSlider):
            self._slider_valor(alvo, x, y)
            self._qt_grab = alvo
            self._pintar()
            return True
        return True

    def _on_motion(self, _w, event):
        try:
            return self._on_motion_ok(event)
        except Exception:
            log.exception("motion")
            return False

    def _on_motion_ok(self, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QSlider
        if self._qt_grab is not None and (event.state & Gdk.ModifierType.BUTTON1_MASK):
            x, y = self._map_xy(event)
            if isinstance(self._qt_grab, QSlider):
                self._slider_valor(self._qt_grab, x, y)
                self._pintar()
            else:
                self._enviar_mouse(self._qt_grab, x, y, event, QEvent.Type.MouseMove)
            return True
        if not self._arrastando:
            return False
        if not (event.state & Gdk.ModifierType.BUTTON1_MASK):
            self._arrastando = False
            return False
        x = int(event.x_root - self._drag_off_x)
        y = int(event.y_root - self._drag_off_y)
        self._pos_manual = True
        self._mover(x, y)
        return True

    def _on_release(self, _w, event):
        try:
            return self._on_release_ok(event)
        except Exception:
            log.exception("release")
            return False

    def _on_release_ok(self, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QSlider
        if event.button == 1 and self._qt_grab is not None:
            x, y = self._map_xy(event)
            if isinstance(self._qt_grab, QSlider):
                self._slider_valor(self._qt_grab, x, y)
            else:
                self._enviar_mouse(self._qt_grab, x, y, event, QEvent.Type.MouseButtonRelease)
            self._qt_grab = None
            self._qt._slider_ativo = None
            self._pintar()
            return True
        if event.button == 1 and self._arrastando:
            self._arrastando = False
            self._salvar_pos()
            return True
        return False

    def _on_scroll(self, _w, event):
        from PySide6.QtWidgets import QScrollArea
        dy = 0.0
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            dy = event.delta_y
        elif event.direction == Gdk.ScrollDirection.UP:
            dy = -1
        elif event.direction == Gdk.ScrollDirection.DOWN:
            dy = 1
        scroll = self._qt.findChild(QScrollArea)
        if scroll is None:
            return False
        bar = scroll.verticalScrollBar()
        bar.setValue(bar.value() + int(dy * 40))
        self._pintar()
        return True

    def _on_key(self, _w, event):
        from PySide6.QtWidgets import QApplication, QLineEdit
        from gi.repository import Gdk as GdkK
        if isinstance(self.get_focus(), Gtk.Entry):
            return False
        foco = self._qt_edit or QApplication.focusWidget()
        if not isinstance(foco, QLineEdit):
            if event.keyval == GdkK.KEY_Escape:
                if self._qt._stack.currentIndex() == 1:
                    self._qt._toggle_config()
                    return True
            return False
        if event.keyval == GdkK.KEY_Escape:
            self._qt._toggle_config()
            return True
        if event.keyval == GdkK.KEY_BackSpace:
            foco.backspace()
            self._pintar()
            return True
        if event.keyval == GdkK.KEY_Delete:
            foco.del_()
            self._pintar()
            return True
        if event.keyval in (GdkK.KEY_Return, GdkK.KEY_KP_Enter):
            return True
        if event.keyval == GdkK.KEY_Left:
            foco.cursorBackward(False)
            self._pintar()
            return True
        if event.keyval == GdkK.KEY_Right:
            foco.cursorForward(False)
            self._pintar()
            return True
        if event.string:
            foco.insert(event.string)
            self._pintar()
            return True
        return False

    def _cor_gtk(self, nome: str, hex_atual: str):
        dlg = Gtk.ColorChooserDialog(title=nome, parent=self)
        rgba = Gdk.RGBA()
        rgba.parse(hex_atual or "#888888")
        dlg.set_rgba(rgba)
        dlg.set_use_alpha(False)
        if dlg.run() == Gtk.ResponseType.OK:
            r = dlg.get_rgba()
            hexc = (
                f"#{int(round(r.red * 255)):02x}"
                f"{int(round(r.green * 255)):02x}"
                f"{int(round(r.blue * 255)):02x}"
            )
            self._qt._pagina_cfg.definir_cor(nome, hexc)
        dlg.destroy()

    def _menu(self, event):
        menu = Gtk.Menu()
        item_v = Gtk.MenuItem(label=t("version", v=VERSAO))
        item_v.set_sensitive(False)
        menu.append(item_v)
        menu.append(Gtk.SeparatorMenuItem())
        pares = (
            (t("menu_settings"), lambda *_: self._qt._toggle_config()),
            (t("menu_reload_weather"), lambda *_: self._qt._buscar_clima()),
            (t("menu_reset_pos"), lambda *_: self._resetar_pos()),
            (t("menu_quit"), lambda *_: self._sair()),
        )
        for rotulo, fn in pares:
            it = Gtk.MenuItem(label=rotulo)
            it.connect("activate", fn)
            menu.append(it)
        menu.show_all()
        menu.popup_at_pointer(event)
        self._menu_ref = menu

    def _geo(self):
        display = Gdk.Display.get_default()
        mon = display.get_primary_monitor() or display.get_monitor(0)
        return mon.get_geometry()

    def _posicionar(self):
        geo = self._geo()
        self._pintar()
        w = max(self.get_allocated_width(), self._qt.width())
        h = max(self.get_allocated_height(), self._qt.height())
        px, py = self._carregar_pos()
        if px < 0 or py < 0:
            px, py = int(POS_X), int(POS_Y)
        self._pos_manual = px >= 0 and py >= 0
        if self._pos_manual:
            x, y = px, py
        else:
            if str(LADO).lower().startswith("esq"):
                x = geo.x + int(MARGEM_DIREITA)
            else:
                x = geo.x + geo.width - w - int(MARGEM_DIREITA)
            y = geo.y + (geo.height - h) // 2
        self._mover(x, y)
        return False

    def _mover(self, x: int, y: int):
        geo = self._geo()
        w = max(1, self._qt.width())
        h = max(1, self._qt.height())
        x = max(geo.x, min(x, geo.x + geo.width - w))
        y = max(geo.y, min(y, geo.y + geo.height - h))
        self._pos_x, self._pos_y = x, y
        if self._ls is not None:
            self._ls.set_margin(self, self._ls.Edge.LEFT, max(0, x - geo.x))
            self._ls.set_margin(self, self._ls.Edge.TOP, max(0, y - geo.y))
        else:
            self.move(x, y)

    def _resetar_pos(self):
        try:
            _POS_ARQ.unlink(missing_ok=True)
        except Exception:
            pass
        self._pos_manual = False
        self._posicionar()

    @staticmethod
    def _carregar_pos():
        try:
            a, b = _POS_ARQ.read_text(encoding="utf-8").split()
            return int(a), int(b)
        except Exception:
            return -1, -1

    def _salvar_pos(self):
        try:
            _POS_ARQ.write_text(f"{self._pos_x} {self._pos_y}\n", encoding="utf-8")
        except Exception as e:
            log.debug("pos: %s", e)

    def _sair(self):
        from PySide6.QtWidgets import QApplication
        try:
            self._qt._espectro.stop()
        except Exception:
            pass
        app = QApplication.instance()
        if app is not None:
            app.quit()
        Gtk.main_quit()


def run(app, lock=None):
    from win.window import WidgetWindows

    app._pop_spot_lock = lock
    qt = WidgetWindows(janela_nativa=False)
    qt.adjustSize()
    host = HostLinux(qt)
    host.show_all()
    Gtk.main()
