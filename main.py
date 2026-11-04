#!/usr/bin/env python3

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from capri import CapriWindow
from capri.audio.recognizer import preload_model_async
from capri.core.settings import get_config_value
from capri.core.user_agent import init_user_agent_async


def main() -> int:
    if get_config_value("audio.voice_enabled", True):
        preload_model_async()
    init_user_agent_async()

    app = QApplication(sys.argv)
    app.setApplicationName("Capri")
    app.setQuitOnLastWindowClosed(False)
    window = CapriWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
