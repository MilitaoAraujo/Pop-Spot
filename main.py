#!/usr/bin/env python3
# Widget de Desktop — Relógio, Clima e Spotify
#
# Para personalizar, edite os arquivos em config/:
#   config/colors.py      — cores e cantos arredondados
#   config/layout.py      — tamanho, posição e fontes
#   config/general.py     — cidade do clima e intervalos
#   config/personalizar.py — cidade, textos, unidade, dias
#
# Dependências:
#   python3-gi, python3-dbus, python3-requests, python3-numpy
#   pulseaudio-utils (para o espectro de áudio)
#   gtk-layer-shell (opcional, para Wayland)

import sys
import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.WARNING)

from window import WidgetDesktop


def main():
    widget = WidgetDesktop()
    widget.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
