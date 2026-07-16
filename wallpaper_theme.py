# Extrai cores do wallpaper e monta um tema pro widget
# Funciona no COSMIC (Pop!_OS) e com fallbacks comuns

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from pathlib import Path

log = logging.getLogger("widget.wallpaper")

_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def localizar_wallpaper() -> str | None:
    """Retorna o caminho da imagem de fundo atual, se houver."""
    home = Path.home()
    candidatos: list[Path] = []

    # COSMIC: estado atual por monitor
    candidatos.append(
        home / ".local/state/cosmic/com.system76.CosmicBackground/v1/wallpapers"
    )
    # COSMIC: config padrão
    candidatos.append(
        Path("/usr/share/cosmic/com.system76.CosmicBackground/v1/all")
    )
    candidatos.append(
        home / ".config/cosmic/com.system76.CosmicBackground/v1/all"
    )

    for arq in candidatos:
        if not arq.is_file():
            continue
        try:
            texto = arq.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r'Path\("([^"]+)"\)', texto):
            p = Path(m.group(1)).expanduser()
            if p.is_file() and p.suffix.lower() in _EXTS:
                return str(p)
        # Cor sólida — sem imagem
        if re.search(r"source:\s*Color\(", texto):
            log.debug("wallpaper é cor sólida em %s", arq)
            return None

    # GNOME / legado
    try:
        import subprocess
        out = subprocess.check_output(
            ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip().strip("'\"")
        if out.startswith("file://"):
            p = Path(out[7:])
            if p.is_file():
                return str(p)
    except Exception:
        pass

    return None


def _hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = (max(0, min(255, int(c))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _misturar(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))  # type: ignore[return-value]


def _luma(rgb: tuple[int, int, int]) -> float:
    r, g, b = (c / 255.0 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _saturacao(rgb: tuple[int, int, int]) -> float:
    r, g, b = (c / 255.0 for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    if mx < 1e-6:
        return 0.0
    return (mx - mn) / mx


def _dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _amostrar_pixbuf(caminho: str, lado: int = 64) -> list[tuple[int, int, int]]:
    import gi
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf

    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(caminho, lado, lado, True)
    if pb is None:
        raise RuntimeError("não foi possível carregar a imagem")
    w, h = pb.get_width(), pb.get_height()
    n = pb.get_n_channels()
    row = pb.get_rowstride()
    data = pb.get_pixels()
    pixels: list[tuple[int, int, int]] = []
    # Amostra grade (pula alguns pixels se muito grande)
    step = 1
    for y in range(0, h, step):
        off = y * row
        for x in range(0, w, step):
            i = off + x * n
            pixels.append((data[i], data[i + 1], data[i + 2]))
    return pixels


def _cores_dominantes(pixels: list[tuple[int, int, int]], n: int = 8) -> list[tuple[int, int, int]]:
    """Quantiza em buckets e devolve as cores mais frequentes."""
    buckets: Counter[tuple[int, int, int]] = Counter()
    for r, g, b in pixels:
        # ignora quase-preto / quase-branco extremos (bordas)
        if r + g + b < 24 or r + g + b > 750:
            continue
        key = (r // 24 * 24 + 12, g // 24 * 24 + 12, b // 24 * 24 + 12)
        buckets[key] += 1
    if not buckets:
        # fallback: usa tudo
        for r, g, b in pixels:
            key = (r // 24 * 24 + 12, g // 24 * 24 + 12, b // 24 * 24 + 12)
            buckets[key] += 1
    ordenadas = [c for c, _ in buckets.most_common(n * 3)]
    # Deduplica por distância
    unicas: list[tuple[int, int, int]] = []
    for c in ordenadas:
        if all(_dist(c, u) > 40 for u in unicas):
            unicas.append(c)
        if len(unicas) >= n:
            break
    return unicas or [(20, 20, 28)]


def montar_tema(caminho: str) -> dict[str, str | float]:
    """
    Gera dict compatível com colors.py:
      COR_BASE, COR_SUPERFICIE, COR_TEXTO, COR_TEXTO_SECUNDARIO,
      COR_TEXTO_TERCIARIO, COR_DESTAQUE, COR_BOTOES_SPOTIFY, OPACIDADE_FUNDO
    """
    pixels = _amostrar_pixbuf(caminho)
    dominantes = _cores_dominantes(pixels)
    media = (
        sum(p[0] for p in pixels) // max(1, len(pixels)),
        sum(p[1] for p in pixels) // max(1, len(pixels)),
        sum(p[2] for p in pixels) // max(1, len(pixels)),
    )
    escuro = _luma(media) < 0.55

    # Fundo: versão bem escura (ou clara) da cor mais comum
    base_src = min(dominantes, key=_luma) if escuro else max(dominantes, key=_luma)
    if escuro:
        cor_base = _misturar(base_src, (8, 8, 14), 0.72)
        cor_superficie = _misturar(base_src, (40, 40, 55), 0.45)
        cor_texto = (230, 230, 235)
        cor_sec = _misturar(cor_texto, cor_base, 0.35)
        cor_ter = _misturar(cor_texto, cor_base, 0.55)
    else:
        cor_base = _misturar(base_src, (245, 245, 248), 0.55)
        cor_superficie = _misturar(base_src, (220, 220, 230), 0.35)
        cor_texto = (20, 20, 28)
        cor_sec = _misturar(cor_texto, cor_base, 0.35)
        cor_ter = _misturar(cor_texto, cor_base, 0.55)

    # Accent: a mais saturada entre as top, longe do fundo
    candidatas = sorted(dominantes, key=_saturacao, reverse=True)
    destaque = candidatas[0]
    for c in candidatas:
        if _saturacao(c) < 0.12:
            continue
        if _dist(c, cor_base) < 50:
            continue
        # precisa contrastar com o texto? não — precisa contrastar com o fundo
        if abs(_luma(c) - _luma(cor_base)) < 0.18:
            # força um pouco mais vibrante
            if escuro:
                c = _misturar(c, (255, 255, 255), 0.25)
            else:
                c = _misturar(c, (0, 0, 0), 0.25)
        destaque = c
        break
    else:
        # pouca saturação: puxa um tom a partir da média
        if escuro:
            destaque = _misturar(media, (160, 120, 220), 0.55)
        else:
            destaque = _misturar(media, (90, 50, 160), 0.45)

    # Garante contraste mínimo destaque × base
    if abs(_luma(destaque) - _luma(cor_base)) < 0.22:
        destaque = _misturar(destaque, (255, 255, 255) if escuro else (0, 0, 0), 0.35)

    return {
        "COR_BASE": _hex(cor_base),
        "COR_SUPERFICIE": _hex(cor_superficie),
        "COR_TEXTO": _hex(cor_texto),
        "COR_TEXTO_SECUNDARIO": _hex(cor_sec),
        "COR_TEXTO_TERCIARIO": _hex(cor_ter),
        "COR_DESTAQUE": _hex(destaque),
        "COR_BOTOES_SPOTIFY": _hex(destaque),
        "OPACIDADE_FUNDO": 0.92,
    }


def adaptar_ao_wallpaper() -> tuple[dict[str, str | float] | None, str | None]:
    """
    Retorna (tema, caminho) ou (None, motivo_erro).
    """
    caminho = localizar_wallpaper()
    if not caminho:
        return None, "Wallpaper não encontrado (use uma imagem nas Configurações do COSMIC)."
    try:
        tema = montar_tema(caminho)
        log.info("tema do wallpaper %s → %s", caminho, tema.get("COR_DESTAQUE"))
        return tema, caminho
    except Exception as e:
        log.warning("falha ao extrair cores: %s", e)
        return None, f"Erro ao ler wallpaper: {e}"


def caminho_estado_cosmic() -> Path:
    return Path.home() / ".local/state/cosmic/com.system76.CosmicBackground/v1/wallpapers"
