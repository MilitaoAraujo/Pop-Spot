#!/usr/bin/env python3
# Widget de Desktop — Relógio, Clima e Spotify
# Desktop Widget — Clock, Weather and Spotify
#
# Para personalizar, edite os arquivos em config/:
# To customize, edit the files inside config/:
#
#   config/colors.py   — cores e cantos arredondados / colors and rounded corners
#   config/layout.py   — tamanho, posição e fontes / size, position and fonts
#   config/general.py  — cidade do clima e intervalos / weather city and intervals
#   config/personalizar.py — cidade, textos, unidade, dias / city, texts, unit, weekdays
#
# Dependências / Dependencies:
#   python3-gi, python3-dbus, python3-requests, python3-numpy, gtk-layer-shell

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.WARNING)

from window import WidgetDesktop


def main():
    widget = WidgetDesktop()
    widget.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
