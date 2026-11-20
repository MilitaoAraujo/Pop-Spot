"""Classe base para plugins de bloco (relógio, clima, mídia, espectro...).

Um plugin não herda de nenhum widget gráfico diretamente: GTK (GObject) e Qt têm
metaclasses próprias, incompatíveis entre si e com ABCMeta por herança múltipla.
Em vez disso, cada plugin cria o widget nativo da toolkit do host dentro de
on_mount() e guarda a referência em self.widget.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseWidgetPlugin(ABC):
    id: str = ""
    nome: str = ""

    def __init__(self) -> None:
        self.widget: Any = None
        self._montado = False

    @abstractmethod
    def on_mount(self, host: Any) -> Any:
        """Cria o widget do bloco e o retorna. `host` é a janela principal."""
        raise NotImplementedError

    def on_update(self) -> None:
        """Chamado periodicamente pelo loop de atualização do host."""

    def on_theme_change(self, cores: dict) -> None:
        """Chamado quando a paleta de cores/tema muda."""

    def on_unload(self) -> None:
        """Chamado ao descarregar o plugin; libera threads/timers/conexões próprias."""

    def montar(self, host: Any) -> Any:
        """Garante que on_mount() rode uma única vez e devolve o widget."""
        if not self._montado:
            self.widget = self.on_mount(host)
            self._montado = True
        return self.widget
