"""Plugin do bloco Relógio/Calendário para a UI em GTK (Linux)."""

from __future__ import annotations

import calendar
import datetime

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from config.i18n import t

from .base import BaseWidgetPlugin

__all__ = ["RelogioPlugin"]


class RelogioPlugin(BaseWidgetPlugin):
    id = "relogio"
    nome = "Relógio/Calendário"

    def __init__(self) -> None:
        super().__init__()
        self.cal_dia = -1

    def on_mount(self, host):
        self.host = host
        self.lbl_hora = host._rotulo("hora", "00", Gtk.Align.START)
        self.lbl_minuto = host._rotulo("minuto", "00", Gtk.Align.START)
        self.lbl_diasem = host._rotulo("diaSemana", "", Gtk.Align.START)
        self.lbl_data = host._rotulo("dataCompleta", "", Gtk.Align.START)

        caixa_clock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for w in (self.lbl_hora, self.lbl_minuto, self.lbl_diasem, self.lbl_data):
            caixa_clock.pack_start(w, False, False, 0)

        self.painel_dir = self._construir_painel_dir(host)

        caixa_relogio = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        caixa_relogio.pack_start(caixa_clock, True, True, 0)
        caixa_relogio.pack_start(self.painel_dir, False, False, 0)

        self._atualizar_calendario()
        self.widget = caixa_relogio
        return caixa_relogio

    def _construir_painel_dir(self, host) -> Gtk.Box:
        painel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        painel.set_valign(Gtk.Align.CENTER)
        painel.set_size_request(95, -1)

        linha_prog = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        linha_prog.set_halign(Gtk.Align.END)
        self.lbl_prog_dia = host._rotulo("progLabel", t("day_progress"), Gtk.Align.END)
        linha_prog.pack_start(self.lbl_prog_dia, False, False, 0)
        self.lbl_prog_pct = host._rotulo("progPct", "0%", Gtk.Align.END)
        linha_prog.pack_start(self.lbl_prog_pct, False, False, 0)
        painel.pack_start(linha_prog, False, False, 0)

        self.barra_dia = Gtk.ProgressBar()
        self.barra_dia.get_style_context().add_class("barDia")
        self.barra_dia.set_show_text(False)
        self.barra_dia.set_fraction(0.0)
        painel.pack_start(self.barra_dia, False, False, 0)

        self.cal_grid = Gtk.Grid()
        self.cal_grid.set_column_spacing(4)
        self.cal_grid.set_row_spacing(3)
        self.cal_grid.set_halign(Gtk.Align.END)
        painel.pack_start(self.cal_grid, False, False, 10)

        return painel

    def _atualizar_calendario(self) -> None:
        for child in list(self.cal_grid.get_children()):
            self.cal_grid.remove(child)

        agora = datetime.datetime.now()
        hoje = agora.day

        for col in range(7):
            lbl = Gtk.Label(label=t(f"cal_{col}"))
            lbl.get_style_context().add_class("calHdr")
            self.cal_grid.attach(lbl, col, 0, 1, 1)

        for row, semana in enumerate(calendar.monthcalendar(agora.year, agora.month)):
            for col, dia in enumerate(semana):
                if dia == 0:
                    lbl = Gtk.Label(label="")
                else:
                    lbl = Gtk.Label(label=str(dia))
                    lbl.get_style_context().add_class("calHoje" if dia == hoje else "calDia")
                self.cal_grid.attach(lbl, col, row + 1, 1, 1)

        self.cal_grid.show_all()

    def on_update(self) -> None:
        agora = datetime.datetime.now()
        self.lbl_hora.set_text(agora.strftime("%H"))
        self.lbl_minuto.set_text(agora.strftime("%M"))
        self.lbl_diasem.set_text(t(f"weekday_{agora.weekday()}").upper())
        self.lbl_data.set_text(f"{agora.day:02d} / {t(f'month_{agora.month}').upper()} / {agora.year}")

        seg = agora.hour * 3600 + agora.minute * 60 + agora.second
        prog = seg / 86400
        self.lbl_prog_pct.set_text(f"{int(prog * 100)}%")
        self.barra_dia.set_fraction(prog)

        if agora.day != self.cal_dia:
            self.cal_dia = agora.day
            self._atualizar_calendario()
