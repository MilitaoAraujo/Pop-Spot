"""QSS a partir das mesmas constantes de config/ do widget GTK."""

from win.scale import px


def gerar_qss() -> str:
    from config import (
        COR_HORA, COR_TEXTO_PRIMARIO, COR_DESTAQUE,
        COR_TEXTO_SECUNDARIO, COR_TEXTO_TERCIARIO, COR_TEXTO_APAGADO,
        COR_SEPARADOR, TAMANHO_FONTE_HORA,
        COR_SUPERFICIE, COR_SUPERFICIE_HOVER,
        COR_BOTOES_SPOTIFY, COR_TEXTO,
    )

    return f"""
QWidget {{
    font-family: 'Inter', 'Segoe UI', 'Ubuntu', 'Noto Sans', sans-serif;
    background: transparent;
    color: {COR_TEXTO};
}}
QLabel#hora, QLabel#minuto {{
    font-size: {px(TAMANHO_FONTE_HORA)}px;
    font-weight: 200;
    color: {COR_HORA};
}}
QLabel#minuto {{ margin-top: -{px(10)}px; }}
QLabel#diaSemana {{
    font-size: {px(10)}px; font-weight: 700;
    color: {COR_TEXTO_SECUNDARIO}; margin-top: {px(6)}px;
}}
QLabel#dataCompleta {{
    font-size: {px(10)}px; color: {COR_TEXTO_TERCIARIO}; margin-top: {px(1)}px;
}}
QFrame#sep {{
    background-color: {COR_SEPARADOR};
    max-height: 1px; min-height: 1px;
    margin-top: {px(18)}px; margin-bottom: {px(18)}px;
}}
QLabel#temperaturaClima {{
    font-size: {px(30)}px; font-weight: 300; color: {COR_TEXTO_PRIMARIO};
}}
QLabel#cidadeClima {{
    font-size: {px(13)}px; font-weight: 700; color: {COR_DESTAQUE}; margin-top: {px(4)}px;
}}
QLabel#descricaoClima {{
    font-size: {px(12)}px; color: {COR_TEXTO_SECUNDARIO}; margin-top: {px(2)}px;
}}
QLabel#detalheClima {{
    font-size: {px(10)}px; color: {COR_TEXTO_TERCIARIO}; margin-top: {px(2)}px;
}}
QLabel#previsaoDia {{
    font-size: {px(10)}px; font-weight: 700; color: {COR_TEXTO_SECUNDARIO};
}}
QLabel#previsaoTemp {{
    font-size: {px(10)}px; color: {COR_TEXTO_TERCIARIO};
}}
QLabel#cabecalhoSpotify {{
    font-size: {px(9)}px; font-weight: 700; color: {COR_DESTAQUE};
}}
QLabel#tituloMusica {{
    font-size: {px(14)}px; font-weight: 700; color: {COR_DESTAQUE}; margin-top: {px(12)}px;
}}
QLabel#artistaMusica {{
    font-size: {px(12)}px; color: {COR_TEXTO_SECUNDARIO}; margin-top: {px(3)}px;
}}
QLabel#albumMusica {{
    font-size: {px(10)}px; color: {COR_TEXTO_TERCIARIO}; margin-top: {px(2)}px;
}}
QLabel#semMusica {{
    font-size: {px(12)}px; color: {COR_TEXTO_APAGADO}; margin-top: {px(10)}px;
}}
QLabel#progLabel {{
    font-size: {px(11)}px; font-weight: 600; color: {COR_TEXTO_SECUNDARIO};
}}
QLabel#progPct {{
    font-size: {px(9)}px; color: {COR_TEXTO_SECUNDARIO};
}}
QLabel#calHdr {{
    font-size: {px(11)}px; font-weight: 700; color: {COR_TEXTO_APAGADO};
}}
QLabel#calDia {{
    font-size: {px(13)}px; color: {COR_TEXTO_SECUNDARIO};
}}
QLabel#calHoje {{
    font-size: {px(13)}px; font-weight: 700; color: {COR_DESTAQUE};
}}
QLabel#tituloConfig {{
    font-size: {px(13)}px; font-weight: 700; color: {COR_DESTAQUE};
    letter-spacing: 1px;
}}
QLabel#dicaConfig, QLabel#statusConfig {{
    font-size: {px(11)}px; color: {COR_TEXTO_APAGADO};
}}
QLabel#labelConfig {{
    font-size: {px(11)}px; font-weight: 600; color: {COR_TEXTO_SECUNDARIO};
}}
QRadioButton#radioConfig, QCheckBox#checkConfig {{
    color: {COR_TEXTO}; font-size: {px(12)}px; spacing: {px(8)}px;
}}
QRadioButton#radioConfig::indicator, QCheckBox#checkConfig::indicator {{
    width: {px(14)}px; height: {px(14)}px;
}}
QLineEdit#entryConfig, QLineEdit#entryHex {{
    background: {COR_SUPERFICIE}; color: {COR_TEXTO};
    border: 1px solid {COR_SEPARADOR}; border-radius: {px(8)}px;
    padding: {px(4)}px {px(8)}px; min-height: {px(26)}px;
    selection-background-color: {COR_DESTAQUE};
}}
QLineEdit#entryConfig[hostFocus="true"], QLineEdit#entryHex[hostFocus="true"] {{
    border: 2px solid {COR_DESTAQUE};
}}
QLineEdit#entryHex {{
    font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: {px(11)}px;
}}
QSlider#scaleConfig, QSlider#scaleVolume {{
    min-height: {px(32)}px;
    padding: {px(10)}px 0;
}}
QSlider#scaleConfig::groove:horizontal, QSlider#scaleVolume::groove:horizontal {{
    height: {px(4)}px; background: {COR_TEXTO_APAGADO}; border-radius: 2px;
}}
QSlider#scaleConfig::handle:horizontal, QSlider#scaleVolume::handle:horizontal {{
    background: {COR_DESTAQUE}; width: {px(14)}px; height: {px(14)}px;
    margin: -{px(5)}px 0; border-radius: {px(7)}px;
}}
QScrollBar:vertical {{
    background: transparent; width: {px(10)}px; margin: 0;
}}
QScrollBar:vertical::handle {{
    background: {COR_TEXTO_APAGADO}; min-height: {px(24)}px; border-radius: 4px;
}}
QScrollBar:vertical::add-line, QScrollBar:vertical::sub-line {{ height: 0; }}
QScrollArea#scrollConfig {{ background: transparent; border: none; }}
QScrollArea#scrollConfig > QWidget > QWidget {{ background: transparent; }}
QListWidget#listaCidades {{
    background: {COR_SUPERFICIE}; color: {COR_TEXTO};
    border: 1px solid {COR_SEPARADOR}; border-radius: {px(8)}px;
    font-size: {px(11)}px;
}}
QPushButton#btnConfig, QPushButton#btnConfigSec {{
    background: {COR_SUPERFICIE}; color: {COR_BOTOES_SPOTIFY};
    border: 1px solid rgba(255,255,255,0.55); border-radius: {px(6)}px;
    padding: {px(6)}px {px(10)}px; min-height: {px(28)}px; font-weight: 600;
    font-size: {px(12)}px;
}}
QPushButton#btnConfig {{ border-color: {COR_DESTAQUE}; }}
QPushButton#btnConfig:hover, QPushButton#btnConfigSec:hover {{
    background: {COR_SUPERFICIE_HOVER}; border-color: {COR_DESTAQUE}; color: {COR_DESTAQUE};
}}
QProgressBar#barDia {{
    border: none; background: {COR_TEXTO_APAGADO};
    min-height: {px(3)}px; max-height: {px(3)}px; border-radius: 2px;
}}
QProgressBar#barDia::chunk {{
    background: {COR_DESTAQUE}; border-radius: 2px;
}}
QPushButton#btnSpotify, QPushButton#btnEngrenagem {{
    background: {COR_SUPERFICIE};
    color: {COR_BOTOES_SPOTIFY};
    border: 1px solid rgba(255,255,255,0.55);
    border-radius: {px(6)}px;
    padding: {px(2)}px {px(6)}px;
    min-height: {px(28)}px;
    min-width: {px(36)}px;
    font-size: {px(14)}px;
}}
QPushButton#btnEngrenagem {{
    border: none; border-radius: {px(8)}px;
    min-width: {px(32)}px; min-height: {px(32)}px;
    font-size: {px(16)}px;
}}
QPushButton#btnSpotify:hover, QPushButton#btnEngrenagem:hover {{
    background: {COR_SUPERFICIE_HOVER};
    border-color: {COR_DESTAQUE};
    color: {COR_DESTAQUE};
}}
QPushButton#btnSpotify:disabled {{
    color: {COR_TEXTO_APAGADO}; opacity: 0.35;
}}
QPushButton#btnCapa {{
    background: {COR_SUPERFICIE}; border: none; border-radius: {px(8)}px; padding: 0;
}}
QFrame#capaPlaceholder {{
    background: {COR_SUPERFICIE};
    border-radius: {px(8)}px;
}}
"""
