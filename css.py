# Gera o CSS completo do widget a partir das constantes de configuração
# Generates the full widget CSS from config constants
from config import (
    COR_FUNDO, RAIO_BORDA, COR_HORA, COR_DATA, COR_TEXTO_PRIMARIO,
    COR_DESTAQUE, COR_TEXTO_SECUNDARIO, COR_TEXTO_APAGADO,
    COR_SEPARADOR, TAMANHO_FONTE_HORA,
    COR_SUPERFICIE, COR_SUPERFICIE_HOVER, COR_SUPERFICIE_ACTIVE, COR_SUPERFICIE_APAGADA,
    COR_BOTOES_SPOTIFY,
)


def gerar_css() -> bytes:
    return f"""
* {{ font-family: 'Inter', 'Ubuntu', 'Noto Sans', sans-serif; }}

/* Garante renderização de emoji no Windows (Segoe UI Emoji) e Linux (Noto Color Emoji) */
.iconeClima {{ font-family: 'Segoe UI Emoji', 'Noto Color Emoji', 'Noto Sans', sans-serif; }}

window {{ background: transparent; }}

/* Fundo principal do widget */
.raiz {{
    background: {COR_FUNDO};
    border-radius: {RAIO_BORDA}px;
    padding: 26px 24px;
}}

/* Números da hora */
.hora, .minuto {{
    font-size: {TAMANHO_FONTE_HORA}px;
    font-weight: 200;
    color: {COR_HORA};
}}
.minuto {{ margin-top: -10px; }}

/* Dia da semana */
.diaSemana {{
    font-size: 10px;
    font-weight: 700;
    color: {COR_DATA};
    margin-top: 6px;
}}

/* Data completa */
.dataCompleta {{
    font-size: 10px;
    color: {COR_DATA};
    margin-top: 1px;
}}

/* Linha divisória */
box.sep {{
    background-color: {COR_SEPARADOR};
    min-height: 1px;
    margin-top: 18px;
    margin-bottom: 18px;
}}

/* Ícone do clima */
.iconeClima {{ font-size: 26px; }}

/* Temperatura */
.temperaturaClima {{
    font-size: 30px;
    font-weight: 300;
    color: {COR_TEXTO_PRIMARIO};
    margin-left: 6px;
}}

/* Nome da cidade */
.cidadeClima {{
    font-size: 13px;
    font-weight: 700;
    color: {COR_DESTAQUE};
    margin-top: 4px;
}}

/* Descrição do clima (ex: Céu limpo) */
.descricaoClima {{
    font-size: 12px;
    color: {COR_TEXTO_SECUNDARIO};
    margin-top: 2px;
}}

/* Vento e umidade */
.detalheClima {{
    font-size: 10px;
    color: {COR_TEXTO_APAGADO};
    margin-top: 2px;
}}

/* Cabeçalho "TOCANDO AGORA" */
.cabecalhoSpotify {{
    font-size: 9px;
    font-weight: 700;
    color: {COR_TEXTO_APAGADO};
}}

/* Título da música */
.tituloMusica {{
    font-size: 14px;
    font-weight: 700;
    color: {COR_DESTAQUE};
    margin-top: 12px;
}}

/* Nome do artista */
.artistaMusica {{
    font-size: 12px;
    color: {COR_TEXTO_SECUNDARIO};
    margin-top: 3px;
}}

/* Nome do álbum */
.albumMusica {{
    font-size: 10px;
    color: {COR_TEXTO_APAGADO};
    margin-top: 2px;
}}

/* Texto quando Spotify não está rodando */
.semMusica {{
    font-size: 12px;
    color: {COR_TEXTO_APAGADO};
    margin-top: 10px;
}}

/* Botões de controle — completamente transparentes, sem borda nem sombra */
button.btnSpotify {{
    min-height: 24px;
    min-width:  30px;
    padding: 2px 6px;
    margin: 0 2px;
    background-color: transparent;
    background-image: none;
    border: none;
    border-radius: 4px;
    box-shadow: none;
    outline: none;
    transition: none;
}}
button.btnSpotify:hover {{
    background-color: transparent;
    background-image: none;
    box-shadow: none;
}}
button.btnSpotify:active {{
    background-color: transparent;
    background-image: none;
    box-shadow: none;
}}
button.btnSpotify:focus {{
    background-color: transparent;
    background-image: none;
    box-shadow: none;
    outline: none;
}}
button.btnSpotify:disabled {{
    background-color: transparent;
    background-image: none;
    box-shadow: none;
}}
button.btnSpotify label {{
    font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji', 'Symbola', sans-serif;
    font-size: 16px;
    color: {COR_BOTOES_SPOTIFY};
}}
button.btnSpotify:hover label {{
    color: {COR_DESTAQUE};
}}
button.btnSpotify:active label {{
    color: {COR_BOTOES_SPOTIFY};
    opacity: 0.6;
}}
button.btnSpotify:disabled label {{
    color: {COR_TEXTO_APAGADO};
}}
button.btnSpotify > * {{
    background-color: transparent;
    background-image: none;
}}

/* Rótulo "Progresso do dia" — um pouco maior que a porcentagem */
.progLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {COR_TEXTO_APAGADO};
}}

/* Porcentagem do dia */
.progPct {{
    font-size: 9px;
    color: {COR_TEXTO_APAGADO};
}}

progressbar.barDia trough {{
    background-color: {COR_TEXTO_APAGADO};
    min-height: 3px;
    border-radius: 2px;
}}

progressbar.barDia trough progress {{
    background-color: {COR_DESTAQUE};
    min-height: 3px;
    border-radius: 2px;
}}

/* Mini calendário */
.calHdr {{
    font-size: 9px;
    font-weight: 700;
    color: {COR_TEXTO_APAGADO};
    padding: 0px 2px;
}}

.calDia {{
    font-size: 10px;
    color: {COR_TEXTO_SECUNDARIO};
    padding: 0px 2px;
}}

.calHoje {{
    font-size: 10px;
    font-weight: 700;
    color: {COR_DESTAQUE};
    padding: 0px 2px;
}}
""".encode()
