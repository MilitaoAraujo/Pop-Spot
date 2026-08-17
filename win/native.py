"""Faz a janela Qt se comportar como widget, não como app (sem borda/taskbar)."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("popspot.win.native")


def _tem_libxcb_cursor() -> bool:
    try:
        import ctypes.util
        if ctypes.util.find_library("xcb-cursor"):
            return True
    except Exception:
        pass
    for p in (
        "/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0",
        "/usr/lib/aarch64-linux-gnu/libxcb-cursor.so.0",
        "/lib/x86_64-linux-gnu/libxcb-cursor.so.0",
        "/usr/lib/libxcb-cursor.so.0",
    ):
        if Path(p).exists():
            return True
    return False


def preparar_plataforma() -> None:
    """Tem de correr antes do QApplication."""
    os.environ["QT_WAYLAND_DISABLE_WINDOWDECORATION"] = "1"
    if not sys.platform.startswith("linux"):
        return
    # COSMIC desenha SSD na dock em xdg-toplevel Wayland.
    # XWayland (xcb) + hints EWMH = sem chrome. Precisa de libxcb-cursor0.
    ja = os.environ.get("QT_QPA_PLATFORM", "").strip()
    if ja and ja != "xcb":
        return
    if _tem_libxcb_cursor():
        os.environ["QT_QPA_PLATFORM"] = "xcb"
        return
    os.environ.pop("QT_QPA_PLATFORM", None)
    print(
        "Pop Spot (teste Qt): instale o cursor X11 para ficar sem borda/dock:\n"
        "    sudo apt install libxcb-cursor0\n"
        "Sem isso, abre no Wayland (pode aparecer como app normal).",
        file=sys.stderr,
    )


def aplicar_como_widget(janela) -> None:
    if sys.platform == "win32":
        _aplicar_hwnd(int(janela.winId()))
        return
    if sys.platform.startswith("linux"):
        _aplicar_x11(int(janela.winId()))
        try:
            janela.lower()
        except Exception:
            pass


def _aplicar_hwnd(hwnd: int) -> None:
    if not hwnd:
        return
    import ctypes

    user32 = ctypes.windll.user32
    gwl_style = -16
    gwl_exstyle = -20
    ws_popup = 0x80000000
    ws_visible = 0x10000000
    ws_caption = 0x00C00000
    ws_thickframe = 0x00040000
    ws_ex_toolwindow = 0x00000080
    ws_ex_appwindow = 0x00040000
    ws_ex_noactivate = 0x08000000
    hwnd_bottom = 1
    swp_nomove = 0x0002
    swp_nosize = 0x0001
    swp_noactivate = 0x0010
    swp_framechanged = 0x0020

    style = user32.GetWindowLongW(hwnd, gwl_style)
    style = (style | ws_popup | ws_visible) & ~ws_caption & ~ws_thickframe
    user32.SetWindowLongW(hwnd, gwl_style, style)

    ex = user32.GetWindowLongW(hwnd, gwl_exstyle)
    ex = (ex | ws_ex_toolwindow | ws_ex_noactivate) & ~ws_ex_appwindow
    user32.SetWindowLongW(hwnd, gwl_exstyle, ex)
    user32.SetWindowPos(
        hwnd,
        hwnd_bottom,
        0,
        0,
        0,
        0,
        swp_nomove | swp_nosize | swp_noactivate | swp_framechanged,
    )


def _aplicar_x11(xid: int) -> None:
    if not xid:
        return
    sid = hex(xid) if xid else "0x0"
    cmds = (
        [
            "xprop", "-id", sid, "-f", "_NET_WM_WINDOW_TYPE", "32a", "-set",
            "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_UTILITY",
        ],
        [
            "xprop", "-id", sid, "-f", "_NET_WM_STATE", "32a", "-set",
            "_NET_WM_STATE",
            "_NET_WM_STATE_SKIP_TASKBAR,_NET_WM_STATE_SKIP_PAGER,"
            "_NET_WM_STATE_BELOW,_NET_WM_STATE_STICKY",
        ],
        [
            "xprop", "-id", sid, "-f", "_MOTIF_WM_HINTS", "32c", "-set",
            "_MOTIF_WM_HINTS", "2, 0, 0, 0, 0",
        ],
        [
            "xprop", "-id", sid, "-remove", "_NET_WM_STRUT",
            "-remove", "_NET_WM_STRUT_PARTIAL",
        ],
    )
    for cmd in cmds:
        try:
            subprocess.run(
                cmd, check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            log.debug("xprop: %s", e)
