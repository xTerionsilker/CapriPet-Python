from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class TestAppLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_headless_window_startup_and_teardown(self) -> None:
        with (
            patch("capri.ui.voice_coordinator.VoiceInput") as mock_voice_cls,
            patch("capri.audio.recognizer.preload_model_async"),
            patch("capri.controllers.orchestrator.DiscordRpcManager"),
            patch("capri.ui.pet_window.SystemEventHook"),
        ):
            mock_voice_inst = MagicMock()
            mock_voice_cls.return_value = mock_voice_inst
            mock_voice_inst.is_listening = False
            mock_voice_inst.is_busy = False

            from capri.ui.pet_window import CapriWindow
            from capri.ui.theme import init_fonts

            init_fonts()
            window = CapriWindow()

            self.assertIsNotNone(window.orchestrator)
            self.assertIsNotNone(window.teleport_controller)

            window.show()
            for _ in range(15):
                QCoreApplication.processEvents()

            self.assertTrue(window._greeted)
            self.assertIsNotNone(window._startup_overlay)

            window._reveal_on_startup()
            for _ in range(5):
                QCoreApplication.processEvents()

            self.assertTrue(window.isVisible())
            self.assertTrue(window._glitch_timer.isActive())

            window._on_startup_finished()
            for _ in range(5):
                QCoreApplication.processEvents()

            window.update()
            for _ in range(5):
                QCoreApplication.processEvents()

            window.set_pose("stay")
            self.assertEqual(window._sprite_manager.current_pose, "thinking")

            window.close()
            for _ in range(5):
                QCoreApplication.processEvents()

            self.assertTrue(window.is_closing)
