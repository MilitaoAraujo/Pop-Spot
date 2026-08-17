"""Escala igual ao GTK: 0.80–1.30 sobre os px de design."""

_ESCALA_MIN = 0.80
_ESCALA_MAX = 1.30


def escala() -> float:
    try:
        from config import ESCALA
        return max(_ESCALA_MIN, min(_ESCALA_MAX, float(ESCALA)))
    except Exception:
        return 1.0


def px(n: float) -> int:
    return max(1, int(round(float(n) * escala())))
