# Cores do widget — edite os valores abaixo para personalizar
# Widget colors — edit the values below to customize

# Fundo principal do widget
COR_BASE       = "#0c0c12"

# Superfície dos botões (play/pause/skip)
COR_SUPERFICIE = "#14141c"

# Texto principal
COR_TEXTO      = "#e0e0e0"

# Cor de destaque — títulos, cidade, nome da música
COR_DESTAQUE   = "#9b59b6"

# Ícones dos botões de controle
COR_BOTOES_SPOTIFY = COR_DESTAQUE

# ── Derivações automáticas — não editar abaixo ────────────────────────────

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
