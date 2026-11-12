"""Тесты модульных страниц вкладок киберпанк-контекстного меню."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

from capri.ui.context_menu_tabs import (
    AudioTabPage,
    CoreTabPage,
    SystemTabPage,
    VisualTabPage,
)


class TestContextMenuTabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.mock_window = MagicMock()
        self.mock_actions = MagicMock()
        self.mock_window.actions = self.mock_actions
        self.mock_window._orchestrator = MagicMock()

    def test_core_tab_page_creation_and_actions(self) -> None:
        page = CoreTabPage(self.mock_window)
        self.assertIsNotNone(page)

        # Trigger summon
        if hasattr(page, "btn_summon"):
            page.btn_summon.click()
            self.mock_window.activate_command_mode.assert_called()

        # Trigger teleport
        if hasattr(page, "btn_teleport"):
            page.btn_teleport.click()
            self.mock_window.activate_teleport.assert_called()

    def test_audio_tab_page_creation(self) -> None:
        page = AudioTabPage(self.mock_window)
        self.assertIsNotNone(page)

    def test_visual_tab_page_creation(self) -> None:
        page = VisualTabPage(self.mock_window)
        self.assertIsNotNone(page)

    def test_system_tab_page_creation(self) -> None:
        page = SystemTabPage(self.mock_window)
        self.assertIsNotNone(page)
        # Terminate action check
        if hasattr(page, "btn_halt"):
            page.btn_halt.click()
            self.mock_window.close.assert_called()


if __name__ == "__main__":
    unittest.main()
