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

import sys

from PySide6.QtWidgets import QApplication

from capri import CapriWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Capri")
    window = CapriWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
