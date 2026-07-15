# Widget de Desktop — Relógio, Clima e Spotify
#
# Personalize em config/:
#   colors.py, layout.py, general.py, personalizar.py, themes.py

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
    WidgetDesktop().show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
