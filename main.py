#!/usr/bin/env python3

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from capri import CapriWindow
from capri.audio.recognizer import preload_model_async
from capri.core.settings import get_config_value


def _prefer_xwayland() -> None:
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

    # Прогреваем Vosk параллельно с инициализацией Qt, чтобы первый триггер
    # обрабатывался без задержки на загрузку модели.
    if get_config_value("audio.voice_enabled", True):
        preload_model_async()

    app = QApplication(sys.argv)
    app.setApplicationName("Capri")
    app.setQuitOnLastWindowClosed(False)
    window = CapriWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
