#!/usr/bin/env python3
"""Entry point for Capri.

The app now lives in the ``capri`` package:
- ``capri.pet_window.CapriWindow`` — video, input and wiring
- ``capri.speech``                — reusable typewriter reply bubble
- ``capri.glitch``                — full-screen click-through glitch overlay
- ``capri.theme``                 — shared styles

Run with:  .venv/bin/python main.py
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from capri import CapriWindow


def _prefer_xwayland() -> None:
    """Let windows be positioned when running on a Wayland session.

    Wayland does not let clients place top-level windows, so the speech
    bubble always ends up where the compositor wants it. XWayland (the X11
    compatibility layer) does allow positioning, so use it when available.
    An explicit QT_QPA_PLATFORM choice is always respected.
    """
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("QT_QPA_PLATFORM"):
        return
    if not os.environ.get("WAYLAND_DISPLAY") or not os.environ.get("DISPLAY"):
        return

    display = os.environ["DISPLAY"]
    if display.startswith(":"):
        number = display[1:].split(".")[0]
        if number and not os.path.exists(f"/tmp/.X11-unix/X{number}"):
            return
    os.environ["QT_QPA_PLATFORM"] = "xcb"


def main() -> int:
    _prefer_xwayland()
    app = QApplication(sys.argv)
    app.setApplicationName("Capri")
    window = CapriWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
