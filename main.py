#!/usr/bin/env python3
"""Точка входа Capri.

Приложение живёт в пакете ``capri``:
- ``capri.pet_window.CapriWindow`` — видео, ввод и связи
- ``capri.speech``                — многоразовое облачко с печатной машинкой
- ``capri.glitch``                — полноэкранный сквозной глитч-оверлей
- ``capri.static_noise``          — фоновый шум, управляемый глитчем
- ``capri.voice``                 — голосовой ввод через микрофон
- ``capri.theme``                 — общие стили

Запуск:  .venv/bin/python main.py
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from capri import CapriWindow


def _prefer_xwayland() -> None:
    """Позволить окнам позиционироваться при работе в сессии Wayland.

    Wayland не разрешает клиентам размещать окна верхнего уровня, поэтому
    облачко с речью всегда оказывается там, куда его положит композитор.
    XWayland (слой совместимости с X11) позволяет позиционировать окна,
    поэтому используем его, когда он доступен. Явно заданный
    ``QT_QPA_PLATFORM`` всегда уважается.
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
