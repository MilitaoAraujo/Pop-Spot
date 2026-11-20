"""Plugin do bloco Clima para a UI em GTK (Linux)."""

from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

import config as cfg
import weather as mod_clima
from config.i18n import t

from .base import BaseWidgetPlugin

__all__ = ["ClimaPlugin"]

log = logging.getLogger("widget.clima")

_ESCALA_MIN = 0.80
_ESCALA_MAX = 1.30


def _escala_f() -> float:
    try:
        return max(_ESCALA_MIN, min(_ESCALA_MAX, float(cfg.ESCALA)))
    except Exception:
        return 1.0


def _px(n: float) -> int:
    return max(1, int(round(float(n) * _escala_f())))


class ClimaPlugin(BaseWidgetPlugin):
    id = "clima"
    nome = "Clima"

    def __init__(self) -> None:
        super().__init__()
        self.codigo_atual = None
        self.previsao_widgets: list[tuple[Gtk.Label, Gtk.Image, Gtk.Label]] = []

    def on_mount(self, host) -> Gtk.Box:
        self.host = host
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        linha_temp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.img_icone = Gtk.Image()
        self.img_icone.get_style_context().add_class("iconeClima")
        self.img_icone.set_size_request(36, 36)
        self.img_icone.set_valign(Gtk.Align.CENTER)
        self.atualizar_icone(None)  # sol padrão enquanto carrega
        self.lbl_temperatura = host._rotulo("temperaturaClima", "--°C", Gtk.Align.START)
        linha_temp.pack_start(self.img_icone, False, False, 0)
        linha_temp.pack_start(self.lbl_temperatura, False, False, 0)
        caixa.pack_start(linha_temp, False, False, 0)

        self.lbl_cidade = host._rotulo("cidadeClima", "--", Gtk.Align.START)
        self.lbl_descricao = host._rotulo("descricaoClima", t("seeking_weather"), Gtk.Align.START)
        self.lbl_detalhe = host._rotulo("detalheClima", "", Gtk.Align.START)
        for w in (self.lbl_cidade, self.lbl_descricao, self.lbl_detalhe):
            caixa.pack_start(w, False, False, 0)

        self.caixa_previsao = self._construir_previsao(host)
        caixa.pack_start(self.caixa_previsao, False, False, 6)

        self.widget = caixa
        return caixa

    def _construir_previsao(self, host) -> Gtk.Box:
        """Linha com previsão de 3 dias: dia + ícone 20px + mín/máx."""
        caixa = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caixa.set_homogeneous(True)
        self.previsao_widgets = []
        for _ in range(3):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col.set_halign(Gtk.Align.START)
            lbl_dia = host._rotulo("previsaoDia", "", Gtk.Align.START)
            img = Gtk.Image()
            img.set_size_request(20, 20)
            lbl_temp = host._rotulo("previsaoTemp", "", Gtk.Align.START)
            col.pack_start(lbl_dia, False, False, 0)
            col.pack_start(img, False, False, 0)
            col.pack_start(lbl_temp, False, False, 0)
            caixa.pack_start(col, True, True, 0)
            self.previsao_widgets.append((lbl_dia, img, lbl_temp))
        return caixa

    def atualizar_icone(self, codigo) -> None:
        """Desenha ícone vetorial do clima (estilo README, sem emoji)."""
        try:
            if codigo is None:
                from weather_icons import SOL, renderizar

                pb = renderizar(SOL, tamanho=_px(36), cor=cfg.COR_TEXTO)
            else:
                pb = mod_clima.icone_pixbuf(int(codigo), tamanho=_px(36), cor=cfg.COR_TEXTO)
            self.img_icone.set_from_pixbuf(pb)
            self.codigo_atual = codigo
        except Exception as e:
            log.warning("ícone clima: %s", e)

    def _atualizar_previsao(self, previsao) -> None:
        for i, (lbl_dia, img, lbl_temp) in enumerate(self.previsao_widgets):
            if i < len(previsao):
                d = previsao[i]
                lbl_dia.set_text(str(d.get("dia", "")).upper())
                try:
                    img.set_from_pixbuf(
                        mod_clima.icone_pixbuf(
                            int(d.get("codigo", 113)), tamanho=_px(20), cor=cfg.COR_TEXTO_SECUNDARIO
                        )
                    )
                except Exception as e:
                    log.debug("ícone previsão: %s", e)
                lbl_temp.set_text(f"{d.get('max_c', '--')}° / {d.get('min_c', '--')}°")
            else:
                lbl_dia.set_text("")
                img.clear()
                lbl_temp.set_text("")

    def buscar(self) -> None:
        """Busca dados do clima na rede; chamar fora da thread principal."""
        dados = mod_clima.buscar()
        GLib.idle_add(self.aplicar, dados)

    def aplicar(self, dados) -> bool:
        if dados:
            self.atualizar_icone(dados["codigo"])
            if cfg.UNIDADE_TEMPERATURA.strip().upper() in ("°F", "F"):
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
            self.lbl_detalhe.set_text(t("wind_hum", vento=dados["vento_ms"], umidade=dados["umidade"]))
            self._atualizar_previsao(dados.get("previsao") or [])
            if cfg.NOTIFICAR_CHUVA_FORTE and not dados.get("cache"):
                try:
                    mod_clima.notificar_chuva_forte(dados)
                except Exception as e:
                    log.debug("notificar chuva: %s", e)
        else:
            self.lbl_cidade.set_text(t("offline"))
            self.lbl_descricao.set_text("")
            self.lbl_detalhe.set_text("")
        GLib.idle_add(self.host._medir_altura_natural)
        return False

    def on_theme_change(self, cores) -> None:
        if self.codigo_atual is not None:
            self.atualizar_icone(self.codigo_atual)
