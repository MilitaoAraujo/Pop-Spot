"""Tela de configurações Qt — mesmos controles do widget GTK."""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from config import (
    CIDADE, LADO, VERSAO, PRESETS, OPACIDADE_FUNDO, ESCALA,
    MOSTRAR_CALENDARIO, MOSTRAR_SPOTIFY, MOSTRAR_ESPECTRO, MOSTRAR_PREVISAO,
    UNIDADE_TEMPERATURA, NOTIFICAR_CHUVA_FORTE, ADAPTAR_WALLPAPER_AUTO,
    COR_BASE, COR_SUPERFICIE, COR_TEXTO, COR_TEXTO_SECUNDARIO,
    COR_TEXTO_TERCIARIO, COR_DESTAQUE, COR_BOTOES_SPOTIFY,
)
from config.i18n import t, idioma
from win.scale import px

log = logging.getLogger("popspot.win.settings")

_RAIZ = Path(__file__).resolve().parent.parent
_ESCALA_MIN, _ESCALA_MAX = 0.80, 1.30

_CORES = (
    ("COR_BASE", "cor_base", COR_BASE),
    ("COR_SUPERFICIE", "cor_superficie", COR_SUPERFICIE),
    ("COR_TEXTO", "cor_texto", COR_TEXTO),
    ("COR_TEXTO_SECUNDARIO", "cor_texto_sec", COR_TEXTO_SECUNDARIO),
    ("COR_TEXTO_TERCIARIO", "cor_texto_ter", COR_TEXTO_TERCIARIO),
    ("COR_DESTAQUE", "cor_destaque", COR_DESTAQUE),
    ("COR_BOTOES_SPOTIFY", "cor_botoes", COR_BOTOES_SPOTIFY),
)

_PRESET_I18N = {
    "Roxo": "preset_roxo",
    "Azul": "preset_azul",
    "Mono": "preset_mono",
    "Verde": "preset_verde",
}


def _gravar_constantes(caminho: Path, valores: dict) -> None:
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
        novo, n = re.subn(
            rf"^({re.escape(nome)}\s*=\s*).*$",
            rf"\g<1>{literal}",
            texto,
            count=1,
            flags=re.M,
        )
        if n == 0:
            raise ValueError(f"constante {nome} não encontrada em {caminho.name}")
        texto = novo
    caminho.write_text(texto, encoding="utf-8")


class PaginaConfig(QWidget):
    salvo = Signal()
    pedir_cor = Signal(str, str)  # nome, hex atual (Linux host)
    wall_pronto = Signal(object, object)
    cidades_prontas = Signal(str, object)

    def __init__(self, janela_nativa: bool = True, parent=None):
        super().__init__(parent)
        self._janela_nativa = janela_nativa
        self._idioma_lock = False
        self._cores_ui: dict[str, tuple[QLineEdit, QPushButton]] = {}
        self._preset_btns: list[tuple[QPushButton, str]] = []
        self._timer_cidade = QTimer(self)
        self._timer_cidade.setSingleShot(True)
        self._timer_cidade.timeout.connect(self._buscar_cidades)
        self.wall_pronto.connect(self._wall_ok, Qt.ConnectionType.QueuedConnection)
        self.cidades_prontas.connect(self._mostrar_cidades, Qt.ConnectionType.QueuedConnection)
        self._montar()
        self.carregar_valores()

    def _lbl(self, nome: str, texto: str) -> QLabel:
        w = QLabel(texto)
        w.setObjectName(nome)
        w.setWordWrap(True)
        w.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        return w

    def _sep(self) -> QWidget:
        s = QWidget()
        s.setObjectName("sep")
        s.setFixedHeight(1)
        return s

    def _montar(self):
        pagina = QVBoxLayout(self)
        pagina.setContentsMargins(0, 0, 0, 0)
        pagina.setSpacing(px(8))

        self.lbl_titulo = self._lbl("tituloConfig", t("settings"))
        self.lbl_dica = self._lbl("dicaConfig", t("settings_hint"))
        self.lbl_versao = self._lbl("dicaConfig", t("version", v=VERSAO))
        pagina.addWidget(self.lbl_titulo)
        pagina.addWidget(self.lbl_dica)
        pagina.addWidget(self.lbl_versao)

        corpo = QWidget()
        corpo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        v = QVBoxLayout(corpo)
        v.setContentsMargins(0, 0, 14, 8)
        v.setSpacing(px(8))
        v.addWidget(self._sep())

        self.lbl_idioma = self._lbl("labelConfig", t("language"))
        v.addWidget(self.lbl_idioma)
        linha = QHBoxLayout()
        linha.setSpacing(px(16))
        self.radio_pt = QRadioButton("Português")
        self.radio_en = QRadioButton("English")
        self.radio_pt.setObjectName("radioConfig")
        self.radio_en.setObjectName("radioConfig")
        grp = QButtonGroup(self)
        grp.addButton(self.radio_pt)
        grp.addButton(self.radio_en)
        self.radio_pt.toggled.connect(self._on_idioma)
        self.radio_en.toggled.connect(self._on_idioma)
        linha.addWidget(self.radio_pt)
        linha.addWidget(self.radio_en)
        linha.addStretch(1)
        v.addLayout(linha)

        self.lbl_cidade = self._lbl("labelConfig", t("city"))
        v.addWidget(self.lbl_cidade)
        linha_c = QHBoxLayout()
        linha_c.setSpacing(px(8))
        self.entry_cidade = QLineEdit()
        self.entry_cidade.setObjectName("entryConfig")
        self.entry_cidade.setPlaceholderText(t("city_placeholder"))
        self.entry_cidade.setMinimumHeight(px(32))
        self.entry_cidade.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.entry_cidade.textChanged.connect(self._on_cidade_texto)
        self.btn_cidade_auto = QPushButton(t("city_auto"))
        self.btn_cidade_auto.setObjectName("btnConfigSec")
        self.btn_cidade_auto.setToolTip(t("city_auto_tip"))
        self.btn_cidade_auto.clicked.connect(self._on_cidade_auto)
        linha_c.addWidget(self.entry_cidade, 1)
        linha_c.addWidget(self.btn_cidade_auto, 0)
        v.addLayout(linha_c)
        self.lista_cidades = QListWidget()
        self.lista_cidades.setObjectName("listaCidades")
        self.lista_cidades.setMaximumHeight(px(90))
        self.lista_cidades.hide()
        self.lista_cidades.itemClicked.connect(self._on_cidade_item)
        v.addWidget(self.lista_cidades)
        self.lbl_dica_cidade = self._lbl("dicaConfig", t("city_hint"))
        v.addWidget(self.lbl_dica_cidade)

        self.chk_chuva = QCheckBox(t("rain_notify"))
        self.chk_chuva.setObjectName("checkConfig")
        v.addWidget(self.chk_chuva)

        self.lbl_unidade = self._lbl("labelConfig", t("temp_unit"))
        v.addWidget(self.lbl_unidade)
        linha_u = QHBoxLayout()
        linha_u.setSpacing(px(16))
        self.radio_c = QRadioButton("°C")
        self.radio_f = QRadioButton("°F")
        for r in (self.radio_c, self.radio_f):
            r.setObjectName("radioConfig")
        g2 = QButtonGroup(self)
        g2.addButton(self.radio_c)
        g2.addButton(self.radio_f)
        linha_u.addWidget(self.radio_c)
        linha_u.addWidget(self.radio_f)
        linha_u.addStretch(1)
        v.addLayout(linha_u)

        self.lbl_lado = self._lbl("labelConfig", t("side"))
        v.addWidget(self.lbl_lado)
        linha_l = QHBoxLayout()
        linha_l.setSpacing(px(16))
        self.radio_dir = QRadioButton(t("side_right"))
        self.radio_esq = QRadioButton(t("side_left"))
        for r in (self.radio_dir, self.radio_esq):
            r.setObjectName("radioConfig")
        g3 = QButtonGroup(self)
        g3.addButton(self.radio_dir)
        g3.addButton(self.radio_esq)
        linha_l.addWidget(self.radio_dir)
        linha_l.addWidget(self.radio_esq)
        linha_l.addStretch(1)
        v.addLayout(linha_l)

        self.chk_autostart = QCheckBox(t("autostart"))
        self.chk_autostart.setObjectName("checkConfig")
        self.chk_autostart.setToolTip(t("autostart_tip"))
        self.chk_autostart.setVisible(sys.platform == "win32")
        self.chk_autostart.toggled.connect(self._on_autostart)
        v.addWidget(self.chk_autostart)

        v.addWidget(self._sep())
        self.lbl_blocos = self._lbl("tituloConfig", t("blocks"))
        v.addWidget(self.lbl_blocos)
        self.chk_calendario = QCheckBox(t("block_calendar"))
        self.chk_spotify = QCheckBox(t("block_spotify"))
        self.chk_espectro = QCheckBox(t("block_spectrum"))
        self.chk_previsao = QCheckBox(t("block_forecast"))
        for c in (self.chk_calendario, self.chk_spotify, self.chk_espectro, self.chk_previsao):
            c.setObjectName("checkConfig")
            v.addWidget(c)

        v.addWidget(self._sep())
        self.lbl_cores = self._lbl("tituloConfig", t("colors"))
        v.addWidget(self.lbl_cores)
        self.lbl_tema = self._lbl("labelConfig", t("quick_theme"))
        v.addWidget(self.lbl_tema)
        nomes = list(PRESETS)
        for i in range(0, len(nomes), 2):
            linha_p = QHBoxLayout()
            linha_p.setSpacing(px(8))
            for nome in nomes[i:i + 2]:
                b = QPushButton(t(_PRESET_I18N.get(nome, nome)))
                b.setObjectName("btnConfigSec")
                b.setMinimumHeight(px(30))
                b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                b.clicked.connect(lambda _=False, n=nome: self._aplicar_preset(n))
                linha_p.addWidget(b)
                self._preset_btns.append((b, nome))
            v.addLayout(linha_p)

        self.btn_wall = QPushButton(t("adapt_wallpaper"))
        self.btn_wall.setObjectName("btnConfig")
        self.btn_wall.setToolTip(t("adapt_wallpaper_tip"))
        self.btn_wall.clicked.connect(self._on_wallpaper)
        v.addWidget(self.btn_wall)
        self.chk_wall_auto = QCheckBox(t("adapt_wallpaper_auto"))
        self.chk_wall_auto.setObjectName("checkConfig")
        v.addWidget(self.chk_wall_auto)
        self.lbl_dica_wall = self._lbl("dicaConfig", t("adapt_wallpaper_hint"))
        v.addWidget(self.lbl_dica_wall)

        self.lbl_tamanho = self._lbl("labelConfig", t("widget_size"))
        v.addWidget(self.lbl_tamanho)
        self.scale_tamanho = QSlider(Qt.Orientation.Horizontal)
        self.scale_tamanho.setObjectName("scaleConfig")
        self.scale_tamanho.setMinimumHeight(px(32))
        self.scale_tamanho.setRange(int(_ESCALA_MIN * 100), int(_ESCALA_MAX * 100))
        self.scale_tamanho.setSingleStep(1)
        self.scale_tamanho.setPageStep(5)
        self.lbl_val_tam = self._lbl("dicaConfig", "")
        self.scale_tamanho.valueChanged.connect(
            lambda n: self.lbl_val_tam.setText(f"{n / 100:.2f}"))
        v.addWidget(self.scale_tamanho)
        v.addWidget(self.lbl_val_tam)
        self.lbl_dica_tam = self._lbl("dicaConfig", t("widget_size_hint"))
        v.addWidget(self.lbl_dica_tam)

        self.lbl_opacidade = self._lbl("labelConfig", t("opacity"))
        v.addWidget(self.lbl_opacidade)
        self.scale_opacidade = QSlider(Qt.Orientation.Horizontal)
        self.scale_opacidade.setObjectName("scaleConfig")
        self.scale_opacidade.setMinimumHeight(px(32))
        self.scale_opacidade.setRange(40, 100)
        self.scale_opacidade.setSingleStep(1)
        self.lbl_val_op = self._lbl("dicaConfig", "")
        self.scale_opacidade.valueChanged.connect(
            lambda n: self.lbl_val_op.setText(f"{n / 100:.2f}"))
        v.addWidget(self.scale_opacidade)
        v.addWidget(self.lbl_val_op)

        self.lbl_dica_cores = self._lbl("dicaConfig", t("colors_hint"))
        v.addWidget(self.lbl_dica_cores)

        self._cores_labels: dict[str, tuple[QLabel, str]] = {}
        for nome, chave, valor in _CORES:
            linha = QHBoxLayout()
            linha.setSpacing(px(8))
            lbl = self._lbl("labelConfig", t(chave))
            entry = QLineEdit(str(valor) if str(valor).startswith("#") else f"#{valor}")
            entry.setObjectName("entryHex")
            entry.setMaxLength(7)
            entry.setFixedWidth(px(78))
            btn = QPushButton()
            btn.setObjectName("btnCor")
            btn.setFixedSize(px(36), px(28))
            btn.setToolTip(t(chave))
            self._pintar_btn_cor(btn, entry.text())
            entry.textChanged.connect(lambda txt, n=nome: self._on_hex(n, txt))
            btn.clicked.connect(lambda _=False, n=nome: self._on_picker(n))
            self._cores_ui[nome] = (entry, btn)
            self._cores_labels[nome] = (lbl, chave)
            linha.addWidget(lbl, 1)
            linha.addWidget(entry)
            linha.addWidget(btn)
            v.addLayout(linha)

        scroll = QScrollArea()
        scroll.setObjectName("scrollConfig")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(corpo)
        scroll.setFixedHeight(px(380))
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._scroll = scroll
        self._corpo = corpo
        pagina.addWidget(scroll, 0)

        linha_b = QHBoxLayout()
        linha_b.setSpacing(px(12))
        self.btn_salvar = QPushButton(t("save"))
        self.btn_salvar.setObjectName("btnConfig")
        self.btn_salvar.clicked.connect(self._on_salvar)
        self.btn_pasta = QPushButton(t("open_config"))
        self.btn_pasta.setObjectName("btnConfigSec")
        self.btn_pasta.clicked.connect(self._on_pasta)
        linha_b.addWidget(self.btn_salvar, 1)
        linha_b.addWidget(self.btn_pasta, 1)
        pagina.addLayout(linha_b)
        self.lbl_status = self._lbl("statusConfig", "")
        pagina.addWidget(self.lbl_status)

    @staticmethod
    def _pintar_btn_cor(btn: QPushButton, hex_cor: str) -> None:
        h = hex_cor if re.fullmatch(r"#[0-9A-Fa-f]{6}", hex_cor or "") else "#888888"
        btn.setStyleSheet(
            f"QPushButton#btnCor {{ background: {h}; border: 1px solid #555; border-radius: 6px; }}"
        )

    def carregar_valores(self) -> None:
        import config as cfg
        self._idioma_lock = True
        try:
            (self.radio_en if idioma() == "en" else self.radio_pt).setChecked(True)
        finally:
            self._idioma_lock = False
        self.entry_cidade.setText(str(getattr(cfg, "CIDADE", "") or ""))
        self.lista_cidades.hide()
        self.chk_chuva.setChecked(bool(getattr(cfg, "NOTIFICAR_CHUVA_FORTE", True)))
        if str(getattr(cfg, "UNIDADE_TEMPERATURA", "°C")).upper() in ("°F", "F"):
            self.radio_f.setChecked(True)
        else:
            self.radio_c.setChecked(True)
        if str(getattr(cfg, "LADO", "direita")).lower().startswith("esq"):
            self.radio_esq.setChecked(True)
        else:
            self.radio_dir.setChecked(True)
        self.chk_calendario.setChecked(bool(getattr(cfg, "MOSTRAR_CALENDARIO", True)))
        self.chk_spotify.setChecked(bool(getattr(cfg, "MOSTRAR_SPOTIFY", True)))
        self.chk_espectro.setChecked(bool(getattr(cfg, "MOSTRAR_ESPECTRO", True)))
        self.chk_previsao.setChecked(bool(getattr(cfg, "MOSTRAR_PREVISAO", True)))
        self.chk_wall_auto.setChecked(bool(getattr(cfg, "ADAPTAR_WALLPAPER_AUTO", False)))
        if sys.platform == "win32":
            try:
                from win.autostart import esta_ligado
                self.chk_autostart.blockSignals(True)
                self.chk_autostart.setChecked(esta_ligado())
                self.chk_autostart.blockSignals(False)
            except Exception:
                pass
        esc = max(_ESCALA_MIN, min(_ESCALA_MAX, float(getattr(cfg, "ESCALA", 1.0))))
        self.scale_tamanho.setValue(int(round(esc * 100)))
        op = max(0.40, min(1.0, float(getattr(cfg, "OPACIDADE_FUNDO", 0.92))))
        self.scale_opacidade.setValue(int(round(op * 100)))
        for nome, _ch, padrao in _CORES:
            val = str(getattr(cfg, nome, padrao))
            entry, btn = self._cores_ui[nome]
            entry.blockSignals(True)
            entry.setText(val if val.startswith("#") else f"#{val}")
            entry.blockSignals(False)
            self._pintar_btn_cor(btn, entry.text())
        self.lbl_status.setText("")
        self._aplicar_idioma()

    def _aplicar_idioma(self) -> None:
        from config.i18n import t
        self.lbl_titulo.setText(t("settings"))
        self.lbl_dica.setText(t("settings_hint"))
        self.lbl_versao.setText(t("version", v=VERSAO))
        self.lbl_idioma.setText(t("language"))
        self.lbl_cidade.setText(t("city"))
        self.entry_cidade.setPlaceholderText(t("city_placeholder"))
        self.btn_cidade_auto.setText(t("city_auto"))
        self.btn_cidade_auto.setToolTip(t("city_auto_tip"))
        self.lbl_dica_cidade.setText(t("city_hint"))
        self.chk_chuva.setText(t("rain_notify"))
        self.lbl_unidade.setText(t("temp_unit"))
        self.lbl_lado.setText(t("side"))
        self.radio_dir.setText(t("side_right"))
        self.radio_esq.setText(t("side_left"))
        self.chk_autostart.setText(t("autostart"))
        self.chk_autostart.setToolTip(t("autostart_tip"))
        self.lbl_blocos.setText(t("blocks"))
        self.chk_calendario.setText(t("block_calendar"))
        self.chk_spotify.setText(t("block_spotify"))
        self.chk_espectro.setText(t("block_spectrum"))
        self.chk_previsao.setText(t("block_forecast"))
        self.lbl_cores.setText(t("colors"))
        self.lbl_tema.setText(t("quick_theme"))
        for b, nome in self._preset_btns:
            b.setText(t(_PRESET_I18N.get(nome, nome)))
        self.btn_wall.setText(t("adapt_wallpaper"))
        self.btn_wall.setToolTip(t("adapt_wallpaper_tip"))
        self.chk_wall_auto.setText(t("adapt_wallpaper_auto"))
        self.lbl_dica_wall.setText(t("adapt_wallpaper_hint"))
        self.lbl_tamanho.setText(t("widget_size"))
        self.lbl_dica_tam.setText(t("widget_size_hint"))
        self.lbl_opacidade.setText(t("opacity"))
        self.lbl_dica_cores.setText(t("colors_hint"))
        for nome, (lbl, chave) in self._cores_labels.items():
            lbl.setText(t(chave))
        self.btn_salvar.setText(t("save"))
        self.btn_pasta.setText(t("open_config"))

    def _on_idioma(self, checked: bool) -> None:
        if self._idioma_lock or not checked:
            return
        lang = "en" if self.radio_en.isChecked() else "pt"
        if lang == idioma():
            self._aplicar_idioma()
            return
        try:
            _gravar_constantes(_RAIZ / "config" / "personalizar.py", {"IDIOMA": lang})
            self._recarregar_modulos()
            self._aplicar_idioma()
            self.lbl_status.setText(t("saved"))
            self.salvo.emit()
        except Exception as e:
            self.lbl_status.setText(t("save_error", e=e))

    def _on_autostart(self, ligado: bool) -> None:
        if sys.platform != "win32":
            return
        try:
            from win import autostart
            ok = autostart.ligar() if ligado else autostart.desligar()
        except Exception as e:
            ok = False
            log.debug("autostart: %s", e)
        if ok:
            self.lbl_status.setText(t("autostart_on") if ligado else t("autostart_off"))
        else:
            self.chk_autostart.blockSignals(True)
            try:
                from win.autostart import esta_ligado
                self.chk_autostart.setChecked(esta_ligado())
            except Exception:
                pass
            self.chk_autostart.blockSignals(False)
            self.lbl_status.setText(t("autostart_error"))

    def _on_cidade_auto(self) -> None:
        self.entry_cidade.setText("")
        self.lista_cidades.hide()
        self.lbl_status.setText(t("auto_apply"))

    def _on_cidade_texto(self, _txt: str) -> None:
        self._timer_cidade.start(350)

    def _buscar_cidades(self) -> None:
        texto = self.entry_cidade.text().strip()
        if len(texto) < 2:
            self.lista_cidades.hide()
            return
        threading.Thread(target=self._bg_cidades, args=(texto,), daemon=True).start()

    def _bg_cidades(self, texto: str) -> None:
        try:
            import weather as mod_clima
            sug = mod_clima.sugerir_cidades(texto)
        except Exception:
            sug = []
        self.cidades_prontas.emit(texto, sug)

    def _mostrar_cidades(self, texto: str, sug: list) -> None:
        if self.entry_cidade.text().strip() != texto:
            return
        self.lista_cidades.clear()
        if not sug:
            self.lista_cidades.hide()
            return
        for s in sug:
            it = QListWidgetItem(s.get("rotulo") or s.get("cidade") or "")
            it.setData(Qt.ItemDataRole.UserRole, s.get("cidade") or "")
            self.lista_cidades.addItem(it)
        self.lista_cidades.show()

    def _on_cidade_item(self, item: QListWidgetItem) -> None:
        cidade = item.data(Qt.ItemDataRole.UserRole) or item.text()
        self.entry_cidade.blockSignals(True)
        self.entry_cidade.setText(str(cidade))
        self.entry_cidade.blockSignals(False)
        self.lista_cidades.hide()

    def _aplicar_preset(self, nome: str) -> None:
        preset = PRESETS.get(nome) or {}
        self._preencher_cores(preset)
        self.lbl_status.setText(t("theme_applied", name=nome))

    def _preencher_cores(self, cores: dict) -> None:
        if "OPACIDADE_FUNDO" in cores:
            self.scale_opacidade.setValue(int(round(float(cores["OPACIDADE_FUNDO"]) * 100)))
        for nome, valor in cores.items():
            if nome not in self._cores_ui or not isinstance(valor, str):
                continue
            entry, btn = self._cores_ui[nome]
            entry.blockSignals(True)
            entry.setText(valor)
            entry.blockSignals(False)
            self._pintar_btn_cor(btn, valor)

    def _on_hex(self, nome: str, texto: str) -> None:
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", texto or ""):
            self._pintar_btn_cor(self._cores_ui[nome][1], texto)

    def _on_picker(self, nome: str) -> None:
        atual = self._cores_ui[nome][0].text().strip()
        if self._janela_nativa:
            cor = QColorDialog.getColor(QColor(atual or "#888888"), self)
            if cor.isValid():
                self.definir_cor(nome, cor.name())
        else:
            self.pedir_cor.emit(nome, atual)

    def definir_cor(self, nome: str, hex_cor: str) -> None:
        if nome not in self._cores_ui:
            return
        entry, btn = self._cores_ui[nome]
        entry.setText(hex_cor.lower())
        self._pintar_btn_cor(btn, hex_cor)

    def _on_wallpaper(self) -> None:
        self.lbl_status.setText(t("reading_wallpaper"))
        threading.Thread(target=self._bg_wall, daemon=True).start()

    def _bg_wall(self) -> None:
        try:
            import wallpaper_theme as mod_wall
            tema, info = mod_wall.adaptar_ao_wallpaper()
        except Exception as e:
            tema, info = None, str(e)
        self.wall_pronto.emit(tema, info)

    def _wall_ok(self, tema, info) -> None:
        if not tema:
            self.lbl_status.setText(info or t("adapt_fail"))
            return
        self._preencher_cores(tema)
        nome = Path(info).name if info else "wallpaper"
        self.lbl_status.setText(t("colors_from", name=nome))

    def _on_pasta(self) -> None:
        pasta = _RAIZ / "config"
        if sys.platform == "win32":
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta)))
        else:
            os.system(f'xdg-open "{pasta}" >/dev/null 2>&1 &')

    def _on_salvar(self) -> None:
        cidade = self.entry_cidade.text().strip()
        unidade = "°F" if self.radio_f.isChecked() else "°C"
        lado = "esquerda" if self.radio_esq.isChecked() else "direita"
        opacidade = round(self.scale_opacidade.value() / 100.0, 2)
        escala = round(self.scale_tamanho.value() / 100.0, 2)
        escala = max(_ESCALA_MIN, min(_ESCALA_MAX, escala))
        cores = {}
        for nome, _ch, _p in _CORES:
            hex_cor = self._cores_ui[nome][0].text().strip()
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", hex_cor, flags=re.I):
                hex_cor = "#ffffff"
            cores[nome] = hex_cor.lower()
        cores["OPACIDADE_FUNDO"] = opacidade
        try:
            _gravar_constantes(_RAIZ / "config" / "personalizar.py", {
                "CIDADE": cidade,
                "IDIOMA": "en" if self.radio_en.isChecked() else "pt",
                "UNIDADE_TEMPERATURA": unidade,
                "MOSTRAR_CALENDARIO": self.chk_calendario.isChecked(),
                "MOSTRAR_SPOTIFY": self.chk_spotify.isChecked(),
                "MOSTRAR_ESPECTRO": self.chk_espectro.isChecked(),
                "MOSTRAR_PREVISAO": self.chk_previsao.isChecked(),
                "NOTIFICAR_CHUVA_FORTE": self.chk_chuva.isChecked(),
                "ADAPTAR_WALLPAPER_AUTO": self.chk_wall_auto.isChecked(),
            })
            _gravar_constantes(_RAIZ / "config" / "colors.py", cores)
            _gravar_constantes(_RAIZ / "config" / "layout.py", {
                "LADO": lado, "POS_X": -1, "POS_Y": -1, "ESCALA": escala,
            })
            try:
                (_RAIZ / "config" / ".widget_pos").unlink(missing_ok=True)
            except Exception:
                pass
            self._recarregar_modulos()
            self._aplicar_idioma()
            self.lbl_status.setText(t("saved"))
            self.salvo.emit()
        except Exception as e:
            self.lbl_status.setText(t("save_error", e=e))
            log.exception("salvar")

    @staticmethod
    def _recarregar_modulos() -> None:
        import importlib
        import config.colors, config.personalizar, config.layout, config.themes, config.i18n, config
        importlib.reload(config.colors)
        importlib.reload(config.personalizar)
        importlib.reload(config.layout)
        importlib.reload(config.themes)
        importlib.reload(config.i18n)
        importlib.reload(config)
