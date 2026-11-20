"""Plugin do bloco Relógio/Calendário para a UI em Qt/PySide6 (Windows)."""

from __future__ import annotations

import calendar
import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QProgressBar, QSizePolicy, QVBoxLayout, QWidget

from config.i18n import t
from win.scale import px

from .base import BaseWidgetPlugin

__all__ = ["RelogioPlugin"]


class RelogioPlugin(BaseWidgetPlugin):
    id = "relogio"
    nome = "Relógio/Calendário"

    def __init__(self) -> None:
        super().__init__()
        self.cal_dia = -1

    def on_mount(self, host) -> QWidget:
        self.host = host
        relogio_linha = QHBoxLayout()
        relogio_linha.setContentsMargins(0, 0, 0, 0)
        relogio_linha.setSpacing(px(12))
        relogio_linha.setAlignment(Qt.AlignmentFlag.AlignTop)

        caixa_clock = QVBoxLayout()
        caixa_clock.setSpacing(0)
        self.lbl_hora = host._rotulo("hora", "00")
        self.lbl_minuto = host._rotulo("minuto", "00")
        self.lbl_diasem = host._rotulo("diaSemana")
        self.lbl_data = host._rotulo("dataCompleta")
        for w in (self.lbl_hora, self.lbl_minuto, self.lbl_diasem, self.lbl_data):
            caixa_clock.addWidget(w)
        relogio_linha.addLayout(caixa_clock, 1)
        relogio_linha.addWidget(self._painel_dir(host))

        container = QWidget()
        container.setLayout(relogio_linha)
        self.widget = container
        return container

    def _painel_dir(self, host) -> QWidget:
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
        self.lbl_prog_dia = host._rotulo("progLabel", t("day_progress"), Qt.AlignmentFlag.AlignRight)
        self.lbl_prog_pct = host._rotulo("progPct", "0%", Qt.AlignmentFlag.AlignRight)
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

        self.cal_grid_host = QWidget()
        self.cal_grid = QGridLayout(self.cal_grid_host)
        self.cal_grid.setContentsMargins(0, px(4), 0, 0)
        self.cal_grid.setHorizontalSpacing(px(6))
        self.cal_grid.setVerticalSpacing(px(5))
        for col in range(7):
            self.cal_grid.setColumnStretch(col, 1)
            self.cal_grid.setColumnMinimumWidth(col, px(20))
        v.addWidget(self.cal_grid_host)

        self.painel_dir_w = painel
        self._atualizar_calendario()
        return painel

    def _atualizar_calendario(self) -> None:
        host = self.host
        while self.cal_grid.count():
            item = self.cal_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        agora = datetime.datetime.now()
        hoje = agora.day
        for col in range(7):
            lbl = host._rotulo("calHdr", t(f"cal_{col}"), Qt.AlignmentFlag.AlignHCenter)
            lbl.setMinimumWidth(px(20))
            self.cal_grid.addWidget(lbl, 0, col)
        for row, semana in enumerate(calendar.monthcalendar(agora.year, agora.month)):
            for col, dia in enumerate(semana):
                if dia == 0:
                    lbl = host._rotulo("calDia", "")
                else:
                    nome = "calHoje" if dia == hoje else "calDia"
                    lbl = host._rotulo(nome, str(dia), Qt.AlignmentFlag.AlignHCenter)
                lbl.setMinimumWidth(px(20))
                lbl.setMinimumHeight(px(16))
                self.cal_grid.addWidget(lbl, row + 1, col)

        self.cal_grid_host.updateGeometry()
        if getattr(self, "painel_dir_w", None) is not None:
            self.painel_dir_w.updateGeometry()

    def on_update(self) -> None:
        agora = datetime.datetime.now()
        self.lbl_hora.setText(agora.strftime("%H"))
        self.lbl_minuto.setText(agora.strftime("%M"))
        self.lbl_diasem.setText(t(f"weekday_{agora.weekday()}").upper())
        self.lbl_data.setText(f"{agora.day:02d} / {t(f'month_{agora.month}').upper()} / {agora.year}")

        seg = agora.hour * 3600 + agora.minute * 60 + agora.second
        prog = seg / 86400
        self.lbl_prog_pct.setText(f"{int(prog * 100)}%")
        self.barra_dia.setValue(int(prog * 1000))

        if agora.day != self.cal_dia:
            self.cal_dia = agora.day
            self._atualizar_calendario()
