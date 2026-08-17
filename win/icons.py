"""Ícones de clima em QPainter (mesmo visual do weather_icons GTK)."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap

SOL = "sol"
NUVEM = "nuvem"
SOL_NUVEM = "sol_nuvem"
CHUVA = "chuva"
SOL_CHUVA = "sol_chuva"
TEMPESTADE = "tempestade"
NEVE = "neve"
NEBLINA = "neblina"


def _pen(cor: str, lw: float) -> QPen:
    p = QPen(QColor(cor))
    p.setWidthF(lw)
    p.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return p


def _sol(p: QPainter, cx, cy, r, raios=True):
    p.drawEllipse(QPointF(cx, cy), r, r)
    if not raios:
        return
    for i in range(8):
        a = i * (2 * math.pi / 8) - math.pi / 2
        p.drawLine(
            QPointF(cx + math.cos(a) * (r + r * 0.28), cy + math.sin(a) * (r + r * 0.28)),
            QPointF(cx + math.cos(a) * (r + r * 0.62), cy + math.sin(a) * (r + r * 0.62)),
        )


def _nuvem(p: QPainter, cx, cy, s):
    path = QPainterPath()
    path.moveTo(cx - s * 0.72, cy + s * 0.18)
    path.cubicTo(
        cx - s * 0.72, cy + s * 0.55,
        cx + s * 0.72, cy + s * 0.55,
        cx + s * 0.72, cy + s * 0.18,
    )
    path.cubicTo(
        cx + s * 0.95, cy + s * 0.18,
        cx + s * 0.95, cy - s * 0.22,
        cx + s * 0.55, cy - s * 0.28,
    )
    path.cubicTo(
        cx + s * 0.55, cy - s * 0.70,
        cx - s * 0.20, cy - s * 0.70,
        cx - s * 0.28, cy - s * 0.30,
    )
    path.cubicTo(
        cx - s * 0.85, cy - s * 0.40,
        cx - s * 0.95, cy + s * 0.05,
        cx - s * 0.72, cy + s * 0.18,
    )
    path.closeSubpath()
    p.drawPath(path)


def _chuva(p: QPainter, cx, cy, s, n=3):
    for i in range(n):
        x = cx - s * 0.32 + i * (s * 0.32)
        y0 = cy + s * 0.42
        p.drawLine(QPointF(x, y0), QPointF(x - s * 0.12, y0 + s * 0.38))


def pix_clima(tipo: str, tamanho: int, cor: str) -> QPixmap:
    size = max(16, int(tamanho))
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(Qt.BrushStyle.NoBrush)
    cx = cy = size / 2
    s = size * 0.38
    p.setPen(_pen(cor, max(1.6, size * 0.055)))

    if tipo == SOL:
        _sol(p, cx, cy, s * 0.55)
    elif tipo == NUVEM:
        _nuvem(p, cx, cy + s * 0.05, s)
    elif tipo == SOL_NUVEM:
        _sol(p, cx + s * 0.35, cy - s * 0.35, s * 0.38)
        _nuvem(p, cx - s * 0.05, cy + s * 0.15, s * 0.85)
    elif tipo == CHUVA:
        _nuvem(p, cx, cy - s * 0.15, s * 0.90)
        _chuva(p, cx, cy - s * 0.05, s)
    elif tipo == SOL_CHUVA:
        _sol(p, cx + s * 0.42, cy - s * 0.42, s * 0.36)
        _nuvem(p, cx - s * 0.05, cy - s * 0.02, s * 0.82)
        _chuva(p, cx, cy + s * 0.05, s * 0.95)
    elif tipo == TEMPESTADE:
        _nuvem(p, cx, cy - s * 0.20, s * 0.90)
        p.drawLine(QPointF(cx - s * 0.05, cy + s * 0.30), QPointF(cx + s * 0.10, cy + s * 0.48))
        p.drawLine(QPointF(cx + s * 0.10, cy + s * 0.48), QPointF(cx - s * 0.08, cy + s * 0.48))
        p.drawLine(QPointF(cx - s * 0.08, cy + s * 0.48), QPointF(cx + s * 0.12, cy + s * 0.78))
        _chuva(p, cx - s * 0.25, cy, s * 0.85, n=2)
    elif tipo == NEVE:
        _nuvem(p, cx, cy - s * 0.18, s * 0.90)
        for i in range(3):
            x = cx - s * 0.30 + i * (s * 0.30)
            y = cy + s * 0.55
            r = s * 0.07
            p.drawEllipse(QPointF(x, y), r, r)
            p.drawLine(QPointF(x - r * 1.4, y), QPointF(x + r * 1.4, y))
            p.drawLine(QPointF(x, y - r * 1.4), QPointF(x, y + r * 1.4))
    elif tipo == NEBLINA:
        for i, (dx, w) in enumerate(((-0.15, 0.9), (0.05, 0.75), (-0.05, 0.85))):
            y = cy - s * 0.15 + i * s * 0.28
            p.drawLine(
                QPointF(cx - s * w * 0.5 + s * dx, y),
                QPointF(cx + s * w * 0.5 + s * dx, y),
            )
    else:
        _sol(p, cx + s * 0.30, cy - s * 0.30, s * 0.35)
        _nuvem(p, cx - s * 0.05, cy + s * 0.10, s * 0.85)
    p.end()
    return QPixmap.fromImage(img)


def pix_nota(tamanho: int, cor: str) -> QPixmap:
    size = max(12, int(tamanho))
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(_pen(cor, max(1.4, size * 0.10)))
    x = size * 0.55
    y0, y1 = size * 0.18, size * 0.72
    p.drawLine(QPointF(x, y0), QPointF(x, y1))
    p.setBrush(QColor(cor))
    p.setPen(Qt.PenStyle.NoPen)
    p.save()
    p.translate(size * 0.38, size * 0.72)
    p.scale(1.0, 0.72)
    p.drawEllipse(QPointF(0, 0), size * 0.18, size * 0.18)
    p.restore()
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(cor, max(1.4, size * 0.10)))
    path = QPainterPath()
    path.moveTo(x, y0)
    path.cubicTo(
        x + size * 0.28, y0 + size * 0.05,
        x + size * 0.28, y0 + size * 0.28,
        x, y0 + size * 0.32,
    )
    p.drawPath(path)
    p.end()
    return QPixmap.fromImage(img)
