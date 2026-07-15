# Ícones de clima vetoriais (estilo linha, como no print do README)
# Desenhados com pycairo → GdkPixbuf (não depende de python3-gi-cairo)

from __future__ import annotations

import math
import gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf

# Tipos de ícone desenháveis
SOL           = "sol"
NUVEM         = "nuvem"
SOL_NUVEM     = "sol_nuvem"
CHUVA         = "chuva"
SOL_CHUVA     = "sol_chuva"   # como no README: sol atrás da nuvem + chuva
TEMPESTADE    = "tempestade"
NEVE          = "neve"
NEBLINA       = "neblina"


def _hex_rgb(cor: str) -> tuple[float, float, float]:
    h = (cor or "#ffffff").strip().lstrip("#")
    if len(h) != 6:
        h = "ffffff"
    return int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0


def _surface_para_pixbuf(surface) -> GdkPixbuf.Pixbuf:
    """Converte cairo.ImageSurface ARGB32 (BGRA LE) → GdkPixbuf RGBA."""
    w = surface.get_width()
    h = surface.get_height()
    stride = surface.get_stride()
    src = memoryview(surface.get_data()).cast("B")
    rgba = bytearray(w * h * 4)
    for y in range(h):
        row = y * stride
        for x in range(w):
            i = row + x * 4
            o = (y * w + x) * 4
            b, g, r, a = src[i], src[i + 1], src[i + 2], src[i + 3]
            rgba[o:o + 4] = bytes((r, g, b, a))
    pb = GdkPixbuf.Pixbuf.new_from_data(
        bytes(rgba),
        GdkPixbuf.Colorspace.RGB,
        True,
        8,
        w,
        h,
        w * 4,
    )
    return pb.copy()  # copia para não depender do buffer temporário


def _stroke(cr, lw: float):
    cr.set_line_width(lw)
    cr.set_line_cap(1)   # ROUND
    cr.set_line_join(1)  # ROUND


def _desenhar_sol(cr, cx, cy, r, com_raios=True, raios=8):
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.stroke()
    if not com_raios:
        return
    for i in range(raios):
        a = i * (2 * math.pi / raios) - math.pi / 2
        x0 = cx + math.cos(a) * (r + r * 0.28)
        y0 = cy + math.sin(a) * (r + r * 0.28)
        x1 = cx + math.cos(a) * (r + r * 0.62)
        y1 = cy + math.sin(a) * (r + r * 0.62)
        cr.move_to(x0, y0)
        cr.line_to(x1, y1)
        cr.stroke()


def _desenhar_nuvem(cr, cx, cy, s):
    """Nuvem em traço contínuo (blob), ancorada em (cx, cy) centro aproximado."""
    # Três lóbulos + base arredondada
    cr.new_path()
    # base esquerda → direita
    cr.move_to(cx - s * 0.72, cy + s * 0.18)
    cr.curve_to(
        cx - s * 0.72, cy + s * 0.55,
        cx + s * 0.72, cy + s * 0.55,
        cx + s * 0.72, cy + s * 0.18,
    )
    # lóbulo direito
    cr.curve_to(
        cx + s * 0.95, cy + s * 0.18,
        cx + s * 0.95, cy - s * 0.22,
        cx + s * 0.55, cy - s * 0.28,
    )
    # lóbulo topo
    cr.curve_to(
        cx + s * 0.55, cy - s * 0.70,
        cx - s * 0.20, cy - s * 0.70,
        cx - s * 0.28, cy - s * 0.30,
    )
    # lóbulo esquerdo
    cr.curve_to(
        cx - s * 0.85, cy - s * 0.40,
        cx - s * 0.95, cy + s * 0.05,
        cx - s * 0.72, cy + s * 0.18,
    )
    cr.close_path()
    cr.stroke()


def _desenhar_chuva(cr, cx, cy, s, n=3):
    """Traços diagonais de chuva sob a nuvem."""
    for i in range(n):
        x = cx - s * 0.32 + i * (s * 0.32)
        y0 = cy + s * 0.42
        cr.move_to(x, y0)
        cr.line_to(x - s * 0.12, y0 + s * 0.38)
        cr.stroke()


def _desenhar_neve(cr, cx, cy, s, n=3):
    for i in range(n):
        x = cx - s * 0.30 + i * (s * 0.30)
        y = cy + s * 0.55
        r = s * 0.07
        cr.arc(x, y, r, 0, 2 * math.pi)
        cr.stroke()
        # cruzinha
        cr.move_to(x - r * 1.4, y)
        cr.line_to(x + r * 1.4, y)
        cr.move_to(x, y - r * 1.4)
        cr.line_to(x, y + r * 1.4)
        cr.stroke()


def _desenhar_raios(cr, cx, cy, s):
    # zig-zag de raio sob a nuvem
    cr.move_to(cx - s * 0.05, cy + s * 0.30)
    cr.line_to(cx + s * 0.10, cy + s * 0.48)
    cr.line_to(cx - s * 0.08, cy + s * 0.48)
    cr.line_to(cx + s * 0.12, cy + s * 0.78)
    cr.stroke()


def _desenhar_neblina(cr, cx, cy, s):
    for i, (dx, w) in enumerate(((-0.15, 0.9), (0.05, 0.75), (-0.05, 0.85))):
        y = cy - s * 0.15 + i * s * 0.28
        x0 = cx - s * w * 0.5 + s * dx
        x1 = cx + s * w * 0.5 + s * dx
        cr.move_to(x0, y)
        cr.line_to(x1, y)
        cr.stroke()


def _desenhar_tipo(cr, tipo: str, size: int):
    cx = size / 2
    cy = size / 2
    s = size * 0.38
    lw = max(1.6, size * 0.055)
    _stroke(cr, lw)

    if tipo == SOL:
        _desenhar_sol(cr, cx, cy, s * 0.55, com_raios=True)

    elif tipo == NUVEM:
        _desenhar_nuvem(cr, cx, cy + s * 0.05, s)

    elif tipo == SOL_NUVEM:
        _desenhar_sol(cr, cx + s * 0.35, cy - s * 0.35, s * 0.38, com_raios=True)
        _desenhar_nuvem(cr, cx - s * 0.05, cy + s * 0.15, s * 0.85)

    elif tipo == CHUVA:
        _desenhar_nuvem(cr, cx, cy - s * 0.15, s * 0.90)
        _desenhar_chuva(cr, cx, cy - s * 0.05, s, n=3)

    elif tipo == SOL_CHUVA:
        # Sol atrás + nuvem + chuva (visual do README)
        _desenhar_sol(cr, cx + s * 0.42, cy - s * 0.42, s * 0.36, com_raios=True)
        _desenhar_nuvem(cr, cx - s * 0.05, cy - s * 0.02, s * 0.82)
        _desenhar_chuva(cr, cx, cy + s * 0.05, s * 0.95, n=3)

    elif tipo == TEMPESTADE:
        _desenhar_nuvem(cr, cx, cy - s * 0.20, s * 0.90)
        _desenhar_raios(cr, cx, cy, s)
        _desenhar_chuva(cr, cx - s * 0.25, cy, s * 0.85, n=2)

    elif tipo == NEVE:
        _desenhar_nuvem(cr, cx, cy - s * 0.18, s * 0.90)
        _desenhar_neve(cr, cx, cy, s, n=3)

    elif tipo == NEBLINA:
        _desenhar_neblina(cr, cx, cy, s)

    else:
        _desenhar_sol(cr, cx + s * 0.30, cy - s * 0.30, s * 0.35, True)
        _desenhar_nuvem(cr, cx - s * 0.05, cy + s * 0.10, s * 0.85)


def renderizar(tipo: str, tamanho: int = 36, cor: str = "#e0e0e0") -> GdkPixbuf.Pixbuf:
    """Gera um GdkPixbuf do ícone de clima desenhado."""
    import cairo

    size = max(16, int(tamanho))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)
    cr.set_operator(cairo.OPERATOR_CLEAR)
    cr.paint()
    cr.set_operator(cairo.OPERATOR_OVER)
    cr.set_source_rgba(*_hex_rgb(cor), 1.0)
    _desenhar_tipo(cr, tipo, size)
    return _surface_para_pixbuf(surface)


def renderizar_nota(tamanho: int = 16, cor: str = "#9b59b6") -> GdkPixbuf.Pixbuf:
    """Nota musical em traço (cabeçalho TOCANDO), estilo linha."""
    import cairo

    size = max(12, int(tamanho))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)
    cr.set_operator(cairo.OPERATOR_CLEAR)
    cr.paint()
    cr.set_operator(cairo.OPERATOR_OVER)
    cr.set_source_rgba(*_hex_rgb(cor), 1.0)
    _stroke(cr, max(1.4, size * 0.10))

    # Haste
    x = size * 0.55
    y0 = size * 0.18
    y1 = size * 0.72
    cr.move_to(x, y0)
    cr.line_to(x, y1)
    cr.stroke()
    # Cabeça (elipse)
    cr.save()
    cr.translate(size * 0.38, size * 0.72)
    cr.scale(1.0, 0.72)
    cr.arc(0, 0, size * 0.18, 0, 2 * math.pi)
    cr.fill()
    cr.restore()
    # Bandeirinha
    cr.move_to(x, y0)
    cr.curve_to(
        x + size * 0.28, y0 + size * 0.05,
        x + size * 0.28, y0 + size * 0.28,
        x, y0 + size * 0.32,
    )
    cr.stroke()
    return _surface_para_pixbuf(surface)
