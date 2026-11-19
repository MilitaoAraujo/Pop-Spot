# Extrai cores do wallpaper e monta um tema pro widget
# Linux: COSMIC / GNOME. Windows: papel de parede do sistema.

from __future__ import annotations

import colorsys
import logging
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

log = logging.getLogger("widget.wallpaper")

_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _localizar_windows() -> str | None:
    import ctypes

    buf = ctypes.create_unicode_buffer(1024)
    spi_get = 0x0073
    ok = ctypes.windll.user32.SystemParametersInfoW(spi_get, len(buf), buf, 0)
    if ok and buf.value:
        p = Path(buf.value)
        if p.is_file():
            return str(p)
    trans = (
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft" / "Windows" / "Themes" / "TranscodedWallpaper"
    )
    if trans.is_file():
        return str(trans)
    return None


def localizar_wallpaper() -> str | None:
    """Retorna o caminho da imagem de fundo atual, se houver."""
    if sys.platform == "win32":
        win = _localizar_windows()
        if win:
            return win

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


def pixels_de_qimage(img, lado: int) -> list[tuple[int, int, int]]:
    """Reduz uma QImage já carregada (de arquivo ou captura de tela) a uma
    lista de pixels RGB — base comum pra qualquer fonte de imagem."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage

    img = img.convertToFormat(QImage.Format.Format_RGB32)
    img = img.scaled(
        lado, lado,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    pixels: list[tuple[int, int, int]] = []
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            pixels.append((c.red(), c.green(), c.blue()))
    if not pixels:
        raise RuntimeError("imagem vazia")
    return pixels


def _amostrar_qimage(caminho: str, lado: int) -> list[tuple[int, int, int]]:
    from PySide6.QtGui import QImage

    img = QImage()
    if not img.load(caminho):
        for fmt in ("JPG", "JPEG", "PNG", "BMP", "WEBP"):
            if img.load(caminho, fmt):
                break
    if img.isNull():
        raise RuntimeError("QImage não carregou a imagem")
    return pixels_de_qimage(img, lado)


def _capturar_desktop_windows():
    """Imprime só a camada do desktop (janela Progman/WorkerW), por trás de
    tudo — ignora o que estiver em primeiro plano (navegador, IDE etc.) e
    continua funcionando com o Wallpaper Engine, que renderiza o fundo
    animado dentro dessa mesma camada. Técnica clássica: força a criação da
    WorkerW com a mensagem 0x052C no Progman, acha a WorkerW certa e usa
    PrintWindow(PW_RENDERFULLCONTENT) nela."""
    import ctypes
    from ctypes import wintypes

    from PySide6.QtGui import QImage

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    progman = user32.FindWindowW("Progman", None)
    if not progman:
        return None
    resultado = ctypes.c_ulong()
    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0x0000, 1000, ctypes.byref(resultado))

    alvo: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        if user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None):
            w = user32.FindWindowExW(0, hwnd, "WorkerW", None)
            if w:
                alvo.append(w)
        return True

    user32.EnumWindows(_enum, 0)
    hwnd = alvo[0] if alvo else progman

    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None

    hdc_janela = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_janela)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_janela, w, h)
    gdi32.SelectObject(hdc_mem, hbmp)
    try:
        PW_RENDERFULLCONTENT = 2
        if not user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT):
            return None

        class _BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32),
            ]
        bmi = _BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bmi.biWidth, bmi.biHeight, bmi.biPlanes, bmi.biBitCount = w, -h, 1, 32
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)
        img = QImage(bytes(buf), w, h, QImage.Format.Format_ARGB32)
        img = img.copy()  # desgruda do buffer local antes de devolver
        return img
    finally:
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_janela)


def capturar_tela(excluir=None):
    """Imagem da área de trabalho de verdade — no Windows, via captura
    dedicada da camada do desktop (funciona com Wallpaper Engine e ignora
    janelas na frente); nos outros sistemas, via print de tela comum.
    `excluir`: QRect (coordenadas de tela) a apagar antes de amostrar —
    só usado no caminho de print de tela comum, pra tirar o próprio widget
    da conta (a captura dedicada do Windows já nunca inclui nossa janela).
    """
    if sys.platform == "win32":
        try:
            img = _capturar_desktop_windows()
            if img is not None and not img.isNull():
                return img
        except Exception as e:
            log.debug("captura do desktop (Windows): %s", e)
        # cai pro print de tela comum se a técnica do WorkerW falhar

    try:
        from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

        telas = QGuiApplication.screens()
        if not telas:
            return None
        geo_total = telas[0].geometry()
        for t in telas[1:]:
            geo_total = geo_total.united(t.geometry())
        img = QImage(geo_total.size(), QImage.Format.Format_RGB32)
        img.fill(QColor(0, 0, 0))
        p = QPainter(img)
        for t in telas:
            g = t.geometry()
            pm = t.grabWindow(0)
            p.drawPixmap(g.x() - geo_total.x(), g.y() - geo_total.y(), pm)
        if excluir is not None:
            ex = excluir.translated(-geo_total.x(), -geo_total.y())
            p.fillRect(ex, QColor(0, 0, 0))
        p.end()
        return img
    except Exception as e:
        log.debug("captura de tela: %s", e)
        return None


def _amostrar_pil(caminho: str, lado: int) -> list[tuple[int, int, int]]:
    from PIL import Image

    with Image.open(caminho) as im:
        im = im.convert("RGB")
        im.thumbnail((lado, lado))
        return list(im.getdata())


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
    for y in range(h):
        off = y * row
        for x in range(w):
            i = off + x * n
            pixels.append((data[i], data[i + 1], data[i + 2]))
    return pixels


def _amostrar(caminho: str, lado: int = 64) -> list[tuple[int, int, int]]:
    if sys.platform == "win32":
        ordem = (_amostrar_qimage, _amostrar_pil, _amostrar_pixbuf)
    else:
        ordem = (_amostrar_pixbuf, _amostrar_qimage, _amostrar_pil)
    erros: list[str] = []
    for fn in ordem:
        try:
            return fn(caminho, lado)
        except Exception as e:
            erros.append(f"{fn.__name__}: {e}")
    raise RuntimeError("; ".join(erros) or "falha ao amostrar wallpaper")


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


def _hls(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (c / 255.0 for c in rgb)
    h, lum, s = colorsys.rgb_to_hls(r, g, b)
    return h, lum, s


def _de_hls(h: float, lum: float, s: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, lum)), max(0.0, min(1.0, s)))
    return (round(r * 255), round(g * 255), round(b * 255))


def _tingir(rgb: tuple[int, int, int], l_alvo: float, s_min: float = 0.0) -> tuple[int, int, int]:
    """Leva a cor pra uma luminosidade-alvo mantendo o matiz (hue) — ao
    contrário de misturar com preto/branco, que lava a cor até ficar
    genérica. `s_min` garante que o resultado não saia quase sem saturação."""
    h, _l, s = _hls(rgb)
    return _de_hls(h, l_alvo, max(s, s_min))


def tema_de_pixels(pixels: list[tuple[int, int, int]]) -> dict[str, str | float]:
    """
    Gera dict compatível com colors.py a partir de uma lista de pixels RGB
    (de um arquivo ou de uma captura de tela):
      COR_BASE, COR_SUPERFICIE, COR_TEXTO, COR_TEXTO_SECUNDARIO,
      COR_TEXTO_TERCIARIO, COR_DESTAQUE, COR_BOTOES_SPOTIFY, OPACIDADE_FUNDO

    Usa HLS (matiz/saturação preservados, só a luminosidade muda) em vez de
    misturar com preto/branco — assim o fundo fica visivelmente tingido da
    cor do wallpaper, não um cinza genérico.
    """
    dominantes = _cores_dominantes(pixels, n=10)
    media = (
        sum(p[0] for p in pixels) // max(1, len(pixels)),
        sum(p[1] for p in pixels) // max(1, len(pixels)),
        sum(p[2] for p in pixels) // max(1, len(pixels)),
    )
    escuro = _luma(media) < 0.55

    # Matiz representativo: a dominante mais saturada — é o tom que o olho
    # reconhece como "a cor do wallpaper". Se a imagem é toda dessaturada
    # (foto em P&B, neblina etc.), cai pra média mesmo.
    mais_saturada = max(dominantes, key=_saturacao)
    matiz_base = mais_saturada if _saturacao(mais_saturada) >= 0.08 else media

    if escuro:
        cor_base = _tingir(matiz_base, 0.10, s_min=0.30)
        cor_superficie = _tingir(matiz_base, 0.20, s_min=0.32)
        cor_texto = (230, 230, 235)
        cor_sec = _misturar(cor_texto, cor_base, 0.35)
        cor_ter = _misturar(cor_texto, cor_base, 0.55)
    else:
        cor_base = _tingir(matiz_base, 0.92, s_min=0.16)
        cor_superficie = _tingir(matiz_base, 0.85, s_min=0.18)
        cor_texto = (20, 20, 28)
        cor_sec = _misturar(cor_texto, cor_base, 0.35)
        cor_ter = _misturar(cor_texto, cor_base, 0.55)

    # Destaque: a dominante mais saturada que tenha um matiz claramente
    # diferente do fundo (senão o acento desaparece dentro do fundo).
    h_base, _l, _s = _hls(cor_base)
    candidatas = sorted(dominantes, key=_saturacao, reverse=True)
    destaque = None
    for c in candidatas:
        if _saturacao(c) < 0.12:
            continue
        h_c, _l_c, s_c = _hls(c)
        dif_matiz = min(abs(h_c - h_base), 1.0 - abs(h_c - h_base))
        if dif_matiz < 0.04 and _dist(c, cor_base) < 60:
            continue  # matiz quase igual ao fundo — não dá acento
        destaque = _tingir(c, 0.58 if escuro else 0.48, s_min=max(0.45, s_c))
        break
    if destaque is None:
        # Nenhuma dominante suficientemente distinta: gira o matiz do fundo
        # pra criar um acento relacionado em vez de puxar roxo genérico.
        destaque = _de_hls((h_base + 0.5) % 1.0, 0.58 if escuro else 0.48, 0.55)

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


def montar_tema(caminho: str) -> dict[str, str | float]:
    """Mesmo resultado de `tema_de_pixels`, lendo os pixels de um arquivo."""
    return tema_de_pixels(_amostrar(caminho, lado=128))


def montar_tema_da_tela(excluir=None) -> dict[str, str | float] | None:
    """Tira um print da área de trabalho e monta o tema a partir dele —
    funciona mesmo quando algo como o Wallpaper Engine desenha o fundo por
    fora do mecanismo nativo (registro/API não bate com o que está na tela)."""
    img = capturar_tela(excluir)
    if img is None:
        return None
    return tema_de_pixels(pixels_de_qimage(img, 128))


def adaptar_ao_wallpaper() -> tuple[dict[str, str | float] | None, str | None]:
    """
    Retorna (tema, caminho) ou (None, motivo_erro).
    """
    caminho = localizar_wallpaper()
    if not caminho:
        return None, "Wallpaper não encontrado. Defina uma imagem de fundo no sistema."
    try:
        tema = montar_tema(caminho)
        log.info("tema do wallpaper %s → %s", caminho, tema.get("COR_DESTAQUE"))
        return tema, caminho
    except Exception as e:
        log.warning("falha ao extrair cores: %s", e)
        return None, f"Erro ao ler wallpaper: {e}"


def caminho_estado_cosmic() -> Path:
    return Path.home() / ".local/state/cosmic/com.system76.CosmicBackground/v1/wallpapers"


def assinatura_wallpaper() -> tuple:
    """Caminho + mtimes para detectar troca de fundo (COSMIC, GNOME ou Windows)."""
    caminho = localizar_wallpaper()
    candidatos: list[Path] = []
    if caminho:
        candidatos.append(Path(caminho))
    candidatos.append(caminho_estado_cosmic())
    if sys.platform == "win32":
        candidatos.append(
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft" / "Windows" / "Themes" / "TranscodedWallpaper"
        )
    mts: list[float | None] = []
    vistos: set[str] = set()
    for p in candidatos:
        chave = str(p)
        if chave in vistos:
            continue
        vistos.add(chave)
        try:
            mts.append(p.stat().st_mtime if p.is_file() else None)
        except OSError:
            mts.append(None)
    return (caminho, tuple(mts))
