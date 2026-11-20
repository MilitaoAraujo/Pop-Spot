"""Presets de cores salvos pelo usuário (diferente de config/themes.py, que são
os presets prontos do projeto). Guardado em JSON, fora do controle de versão.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger("widget.presets_usuario")

_ARQUIVO = Path(__file__).resolve().parent / "presets_usuario.json"


def carregar() -> dict:
    try:
        if not _ARQUIVO.exists():
            return {}
        dados = json.loads(_ARQUIVO.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except Exception as e:
        log.warning("carregar presets do usuário: %s", e)
        return {}


def salvar(nome: str, cores: dict) -> None:
    nome = nome.strip()
    if not nome:
        raise ValueError("nome do preset não pode ser vazio")
    presets = carregar()
    presets[nome] = cores
    _ARQUIVO.write_text(json.dumps(presets, indent=2, ensure_ascii=False), encoding="utf-8")


def remover(nome: str) -> None:
    presets = carregar()
    if presets.pop(nome, None) is not None:
        _ARQUIVO.write_text(json.dumps(presets, indent=2, ensure_ascii=False), encoding="utf-8")
