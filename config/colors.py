# Lê as cores do arquivo colors.css (edite lá — tem seletor de cor nativo)
import re as _re
from pathlib import Path as _Path

def _ler_css() -> dict:
    """Extrai variáveis CSS custom properties de colors.css."""
    css_path = _Path(__file__).parent / "colors.css"
    if not css_path.exists():
        return {}
    texto = css_path.read_text("utf-8")
    return {
        m.group(1).strip(): m.group(2).strip()
        for m in _re.finditer(r"--([^:]+):\s*(#[0-9a-fA-F]{3,8})", texto)
    }

_CSS = _ler_css()

def _c(chave: str, padrao: str) -> str:
    return _CSS.get(chave, padrao)

# ── Cores principais (editáveis em colors.css) ─────────────────────────────
COR_BASE       = _c("cor-base",       "#0c0c12")
COR_SUPERFICIE = _c("cor-superficie", "#14141c")
COR_TEXTO      = _c("cor-texto",      "#e0e0e0")
COR_DESTAQUE   = _c("cor-destaque",   "#9b59b6")
COR_TERCIARIA  = _c("cor-terciaria",  "#9b59b6")
COR_BOTOES_SPOTIFY = _c("cor-botoes", COR_DESTAQUE)

# ── Derivações automáticas ─────────────────────────────────────────────────

def _hex_para_rgb(cor: str) -> tuple[int, int, int]:
    h = cor.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def _rgba(cor: str, alpha: float) -> str:
    r, g, b = _hex_para_rgb(cor)
    return f"rgba({r}, {g}, {b}, {alpha})"

def _misturar(cor: str, alvo: str, t: float) -> str:
    r1, g1, b1 = _hex_para_rgb(cor)
    r2, g2, b2 = _hex_para_rgb(alvo)
    r = int(round(r1 + (r2 - r1) * t))
    g = int(round(g1 + (g2 - g1) * t))
    b = int(round(b1 + (b2 - b1) * t))
    return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"


RAIO_BORDA           = 20
COR_FUNDO            = _rgba(COR_BASE, 0.93)
COR_HORA             = COR_TEXTO
COR_DATA             = _rgba(COR_TEXTO, 0.45)
COR_TEXTO_PRIMARIO   = COR_TEXTO
COR_TEXTO_SECUNDARIO = _rgba(COR_TEXTO, 0.60)
COR_TEXTO_APAGADO    = _rgba(COR_TEXTO, 0.28)
COR_SEPARADOR        = COR_TEXTO_SECUNDARIO

COR_SUPERFICIE_HOVER   = _misturar(COR_SUPERFICIE, "#ffffff", 0.10)
COR_SUPERFICIE_ACTIVE  = _misturar(COR_SUPERFICIE, "#000000", 0.14)
COR_SUPERFICIE_APAGADA = _misturar(COR_SUPERFICIE, "#000000", 0.10)
