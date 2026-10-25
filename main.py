#!/usr/bin/env python3
"""Точка входа Capri.

Приложение живёт в пакете ``capri``:
- ``capri.pet_window.CapriWindow`` — видео, ввод и связи
- ``capri.speech``                — многоразовое облачко с печатной машинкой
- ``capri.glitch``                — полноэкранный сквозной глитч-оверлей
- ``capri.static_noise``          — фоновый шум, управляемый глитчем
- ``capri.voice``                 — голосовой ввод через микрофон
- ``capri.theme``                 — общие стили

Запуск на Windows 11:  .venv\\Scripts\\python.exe main.py
(или двойным кликом по ``run_capri.vbs``, если включена автозагрузка)
"""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtWidgets import QApplication

from capri import CapriWindow


def _enable_per_monitor_dpi() -> None:
    """Включить масштабирование Per-Monitor v2 на Windows 11.

    Windows 11 почти всегда работает с масштабом 125–250 %. Без явного DPI-
    контекста Qt получает системное масштабирование: координаты экранов
    искажаются, глитч-оверлеи закрывают только часть дисплея, а облачко с
    речью ставится не туда. ``SetProcessDpiAwarenessContext`` нужно вызвать
    до создания ``QApplication``; на других платформах функция ничего не
    делает.
    """
    if not sys.platform.startswith("win"):
        return
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = (-4).
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        # До Windows 10 1703 контекста нет — берём версию для Windows 8.1.
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError, ValueError):
            pass


def main() -> int:
    _enable_per_monitor_dpi()
    app = QApplication(sys.argv)
    app.setApplicationName("Capri")
    window = CapriWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
