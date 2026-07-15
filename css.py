# Gera o CSS do widget a partir das constantes atuais de config


def gerar_css() -> bytes:
    from config import (
        COR_FUNDO, RAIO_BORDA, COR_HORA, COR_TEXTO_PRIMARIO,
        COR_DESTAQUE, COR_TEXTO_SECUNDARIO, COR_TEXTO_TERCIARIO, COR_TEXTO_APAGADO,
        COR_SEPARADOR, TAMANHO_FONTE_HORA,
        COR_SUPERFICIE, COR_SUPERFICIE_HOVER,
        COR_BOTOES_SPOTIFY, COR_TEXTO, ESCALA,
    )

    e = max(0.80, min(1.30, float(ESCALA)))

    def px(n: float) -> int:
        return max(1, int(round(float(n) * e)))

    return f"""
* {{ font-family: 'Inter', 'Ubuntu', 'Noto Sans', sans-serif; }}
window {{ background: transparent; }}
.raiz {{
    background: {COR_FUNDO};
    border-radius: {px(RAIO_BORDA)}px;
    padding: {px(26)}px {px(24)}px;
}}
.hora, .minuto {{
    font-size: {px(TAMANHO_FONTE_HORA)}px; font-weight: 200; color: {COR_HORA};
}}
.minuto {{ margin-top: -{px(10)}px; }}
.diaSemana {{ font-size: {px(10)}px; font-weight: 700; color: {COR_TEXTO_SECUNDARIO}; margin-top: {px(6)}px; }}
.dataCompleta {{ font-size: {px(10)}px; color: {COR_TEXTO_TERCIARIO}; margin-top: {px(1)}px; }}
box.sep {{
    background-color: {COR_SEPARADOR}; min-height: 1px;
    margin-top: {px(18)}px; margin-bottom: {px(18)}px;
}}
image.iconeClima {{ margin-right: {px(2)}px; }}
.temperaturaClima {{ font-size: {px(30)}px; font-weight: 300; color: {COR_TEXTO_PRIMARIO}; margin-left: {px(6)}px; }}
.cidadeClima {{ font-size: {px(13)}px; font-weight: 700; color: {COR_DESTAQUE}; margin-top: {px(4)}px; }}
.descricaoClima {{ font-size: {px(12)}px; color: {COR_TEXTO_SECUNDARIO}; margin-top: {px(2)}px; }}
.detalheClima {{ font-size: {px(10)}px; color: {COR_TEXTO_TERCIARIO}; margin-top: {px(2)}px; }}
.previsaoDia {{ font-size: {px(10)}px; font-weight: 700; color: {COR_TEXTO_SECUNDARIO}; }}
.previsaoTemp {{ font-size: {px(10)}px; color: {COR_TEXTO_TERCIARIO}; }}
.cabecalhoSpotify {{ font-size: {px(9)}px; font-weight: 700; color: {COR_DESTAQUE}; }}
.tituloMusica {{ font-size: {px(14)}px; font-weight: 700; color: {COR_DESTAQUE}; margin-top: {px(12)}px; }}
.artistaMusica {{ font-size: {px(12)}px; color: {COR_TEXTO_SECUNDARIO}; margin-top: {px(3)}px; }}
.albumMusica {{ font-size: {px(10)}px; color: {COR_TEXTO_TERCIARIO}; margin-top: {px(2)}px; }}
.semMusica {{ font-size: {px(12)}px; color: {COR_TEXTO_APAGADO}; margin-top: {px(10)}px; }}
button.btnSpotify {{
    background-color: {COR_SUPERFICIE}; padding: {px(2)}px {px(8)}px; margin: 0 {px(2)}px;
    min-height: {px(28)}px; min-width: {px(48)}px; border: 1px solid rgba(255,255,255,0.55);
    border-radius: {px(6)}px; box-shadow: none; outline: none;
}}
button.btnSpotify label {{
    font-family: 'Segoe UI Symbol', 'Noto Sans Symbols2', 'Noto Sans Symbols', sans-serif;
    font-size: {px(14)}px; color: {COR_BOTOES_SPOTIFY};
}}
button.btnSpotify:hover {{ background-color: {COR_SUPERFICIE_HOVER}; border-color: {COR_DESTAQUE}; }}
button.btnSpotify:hover label {{ color: {COR_DESTAQUE}; }}
button.btnSpotify:active {{ opacity: 0.75; }}
button.btnSpotify:disabled {{ opacity: 0.35; }}
button.btnSpotify:disabled label {{ color: {COR_TEXTO_APAGADO}; }}
.specBar {{ background-color: {COR_DESTAQUE}; border-radius: 1px; min-width: {px(4)}px; }}
.progLabel {{ font-size: {px(11)}px; font-weight: 600; color: {COR_TEXTO_SECUNDARIO}; }}
.progPct {{ font-size: {px(9)}px; color: {COR_TEXTO_SECUNDARIO}; }}
progressbar.barDia {{ border: none; box-shadow: none; }}
progressbar.barDia trough {{
    background-color: {COR_TEXTO_APAGADO}; min-height: {px(3)}px; border-radius: 2px; border: none;
}}
progressbar.barDia trough progress {{
    background-color: {COR_DESTAQUE}; min-height: {px(3)}px; border-radius: 2px; border: none;
}}
.calHdr {{ font-size: {px(9)}px; font-weight: 700; color: {COR_TEXTO_APAGADO}; padding: 0 {px(2)}px; }}
.calDia {{ font-size: {px(10)}px; color: {COR_TEXTO_SECUNDARIO}; padding: 0 {px(2)}px; }}
.calHoje {{ font-size: {px(10)}px; font-weight: 700; color: {COR_DESTAQUE}; padding: 0 {px(2)}px; }}
.tituloConfig {{ font-size: {px(13)}px; font-weight: 700; color: {COR_DESTAQUE}; letter-spacing: 1px; }}
.dicaConfig {{ font-size: {px(11)}px; color: {COR_TEXTO_APAGADO}; margin-top: {px(2)}px; }}
.labelConfig {{ font-size: {px(11)}px; font-weight: 600; color: {COR_TEXTO_SECUNDARIO}; margin-top: {px(4)}px; }}
.statusConfig {{ font-size: {px(11)}px; color: {COR_TEXTO_APAGADO}; margin-top: {px(6)}px; }}
entry.entryConfig {{
    background-color: {COR_SUPERFICIE}; color: {COR_TEXTO}; border: 1px solid {COR_SEPARADOR};
    border-radius: {px(8)}px; padding: {px(6)}px {px(10)}px; min-height: {px(28)}px; caret-color: {COR_DESTAQUE};
}}
entry.entryConfig:focus {{ border-color: {COR_DESTAQUE}; }}
radiobutton.radioConfig {{ color: {COR_TEXTO}; font-size: {px(13)}px; }}
radiobutton.radioConfig indicator {{
    min-width: {px(14)}px; min-height: {px(14)}px; border-radius: 50%;
    border: 1px solid {COR_TEXTO_SECUNDARIO}; background: {COR_SUPERFICIE};
}}
radiobutton.radioConfig:checked indicator {{ background: {COR_DESTAQUE}; border-color: {COR_DESTAQUE}; }}
checkbutton.checkConfig {{ color: {COR_TEXTO}; font-size: {px(12)}px; }}
button.btnConfig, button.btnConfigSec {{
    background-image: none; background-color: {COR_SUPERFICIE}; color: {COR_BOTOES_SPOTIFY};
    border: 1px solid rgba(255,255,255,0.55); border-radius: {px(6)}px; padding: {px(6)}px {px(12)}px;
    min-height: {px(28)}px; box-shadow: none; outline: none;
}}
button.btnConfig label, button.btnConfigSec label {{
    color: {COR_BOTOES_SPOTIFY}; font-weight: 600; font-size: {px(12)}px;
}}
button.btnConfig:hover, button.btnConfigSec:hover {{
    background-color: {COR_SUPERFICIE_HOVER}; border-color: {COR_DESTAQUE};
}}
button.btnConfig:hover label, button.btnConfigSec:hover label {{ color: {COR_DESTAQUE}; }}
button.btnConfig:active, button.btnConfigSec:active {{ opacity: 0.75; }}
button.btnConfig {{ border-color: {COR_DESTAQUE}; }}
button.btnEngrenagem {{
    background-image: none; background-color: {COR_SUPERFICIE}; color: {COR_BOTOES_SPOTIFY};
    border: none; border-radius: {px(8)}px; padding: {px(2)}px 0; min-width: {px(32)}px; min-height: {px(32)}px;
}}
button.btnEngrenagem label {{
    font-family: 'Segoe UI Symbol', 'Noto Sans Symbols2', 'Noto Sans Symbols', sans-serif;
    font-size: {px(16)}px; color: {COR_BOTOES_SPOTIFY};
}}
button.btnEngrenagem:hover, button.btnEngrenagemAtivo {{ background-color: {COR_SUPERFICIE_HOVER}; }}
button.btnEngrenagemAtivo label {{ color: {COR_DESTAQUE}; }}
entry.entryHex {{
    min-width: {px(78)}px; font-family: 'JetBrains Mono', 'Ubuntu Mono', 'Consolas', monospace;
    font-size: {px(11)}px; padding: {px(4)}px {px(6)}px;
}}
button.btnCor {{ border: 1px solid {COR_SEPARADOR}; border-radius: {px(6)}px; padding: 0; min-width: {px(36)}px; min-height: {px(28)}px; }}
button.btnCor:hover {{ border-color: {COR_DESTAQUE}; }}
scale.scaleConfig {{ margin-top: {px(2)}px; color: {COR_TEXTO_SECUNDARIO}; }}
scale.scaleConfig trough {{ background-color: {COR_SUPERFICIE}; min-height: {px(4)}px; border-radius: 2px; }}
scale.scaleConfig highlight {{ background-color: {COR_DESTAQUE}; border-radius: 2px; }}
scale.scaleVolume {{ min-width: {px(80)}px; margin-left: {px(4)}px; }}
scale.scaleVolume trough {{ background-color: {COR_SUPERFICIE}; min-height: {px(4)}px; border-radius: 2px; }}
scale.scaleVolume highlight {{ background-color: {COR_DESTAQUE}; border-radius: 2px; }}
""".encode()
