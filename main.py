#!/usr/bin/env python3
"""Main application entry point for CapriPet desktop companion."""

from __future__ import annotations

import sys

from PySide6.QtCore import QLoggingCategory
from PySide6.QtWidgets import QApplication

from capri import CapriWindow
from capri.audio.recognizer import preload_model_async
from capri.core.settings import get_config_value, init_user_agent_async
from capri.ui.speech_sfx import preload_sfx_cache_async
from capri.ui.theme import get_font, init_fonts


def main() -> int:
    QLoggingCategory.setFilterRules("qt.multimedia*=false")
    preload_sfx_cache_async()
    if get_config_value("audio.voice_enabled", True):
        preload_model_async()
    init_user_agent_async()

    app = QApplication(sys.argv)
    app.setApplicationName("Capri")
    app.setQuitOnLastWindowClosed(False)
    init_fonts()
    app.setFont(get_font(12))
    window = CapriWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
