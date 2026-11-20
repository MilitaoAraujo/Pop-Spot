"""Plugin do bloco Clima para a UI em Qt/PySide6 (Windows)."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from config.i18n import t
from win.icons import pix_clima
from win.scale import px

from .base import BaseWidgetPlugin

__all__ = ["ClimaPlugin"]

log = logging.getLogger("widget.clima")


class ClimaPlugin(BaseWidgetPlugin):
    id = "clima"
    nome = "Clima"

    def __init__(self) -> None:
        super().__init__()
        self.codigo_atual = None
        self.previsao_widgets: list[tuple[QLabel, QLabel, QLabel]] = []

    def on_mount(self, host) -> QWidget:
        self.host = host
        container = QWidget()
        col = QVBoxLayout(container)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        linha_temp = QHBoxLayout()
        linha_temp.setSpacing(px(6))
        self.img_icone = QLabel()
        self.img_icone.setFixedSize(px(36), px(36))
        self.atualizar_icone(None)
        self.lbl_temperatura = host._rotulo("temperaturaClima", "--°C")
        linha_temp.addWidget(self.img_icone, 0, Qt.AlignmentFlag.AlignVCenter)
        linha_temp.addWidget(self.lbl_temperatura, 0, Qt.AlignmentFlag.AlignVCenter)
        linha_temp.addStretch(1)
        col.addLayout(linha_temp)

        self.lbl_cidade = host._rotulo("cidadeClima", "--")
        self.lbl_descricao = host._rotulo("descricaoClima", t("seeking_weather"))
        self.lbl_detalhe = host._rotulo("detalheClima")
        col.addWidget(self.lbl_cidade)
        col.addWidget(self.lbl_descricao)
        col.addWidget(self.lbl_detalhe)
        col.addSpacing(px(6))

        self.caixa_previsao = self._construir_previsao(host)
        col.addWidget(self.caixa_previsao)

        self.widget = container
        return container

    def _construir_previsao(self, host) -> QWidget:
        caixa = QWidget()
        linha = QHBoxLayout(caixa)
        linha.setContentsMargins(0, 0, 0, 0)
        linha.setSpacing(px(10))
        self.previsao_widgets = []
        for _ in range(3):
            col = QVBoxLayout()
            col.setSpacing(px(2))
            lbl_dia = host._rotulo("previsaoDia")
            img = QLabel()
            img.setFixedSize(px(20), px(20))
            lbl_temp = host._rotulo("previsaoTemp")
            col.addWidget(lbl_dia)
            col.addWidget(img)
            col.addWidget(lbl_temp)
            w = QWidget()
            w.setLayout(col)
            linha.addWidget(w, 1)
            self.previsao_widgets.append((lbl_dia, img, lbl_temp))
        return caixa

    def atualizar_icone(self, codigo) -> None:
        from config import COR_TEXTO

        try:
            import weather as mod_clima

            tipo = mod_clima.SOL if codigo is None else mod_clima.tipo_icone(int(codigo))
        except Exception:
            tipo = "sol"
        self.img_icone.setPixmap(pix_clima(tipo, px(36), COR_TEXTO))
        self.codigo_atual = codigo

    def buscar(self) -> None:
        """Busca dados do clima na rede; chamar fora da thread principal."""
        try:
            import weather as mod_clima

            dados = mod_clima.buscar()
        except Exception as e:
            log.warning("clima: %s", e)
            dados = None
        self.host.clima_pronto.emit(dados)

    def aplicar(self, dados) -> None:
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
        self.atualizar_icone(dados.get("codigo"))
        self.lbl_temperatura.setText(f"{temp}{unidade}")
        self.lbl_cidade.setText(str(dados.get("cidade") or "--"))
        self.lbl_descricao.setText(str(dados.get("descricao") or ""))
        self.lbl_detalhe.setText(
            t("wind_hum", vento=dados.get("vento_ms", "--"), umidade=dados.get("umidade", "--"))
        )
        previsao = dados.get("previsao") or []
        import weather as mod_clima
        from config import COR_TEXTO_SECUNDARIO

        for i, (lbl_dia, img, lbl_temp) in enumerate(self.previsao_widgets):
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

    def on_theme_change(self, cores) -> None:
        self.atualizar_icone(self.codigo_atual)
