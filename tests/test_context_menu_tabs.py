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

        page.btn_summon.click()
        self.mock_window.activate_command_mode.assert_called()

        page.btn_deck.click()
        self.mock_window.open_console.assert_called()

        page.btn_teleport.click()
        self.mock_window.activate_teleport.assert_called()

    def test_audio_tab_page_volume_slider_step_and_presets(self) -> None:
        page = AudioTabPage(self.mock_window)
        self.assertIsNotNone(page)
        self.assertEqual(page.slider_vol.singleStep(), 25)

        # Click preset 75%
        page._preset_buttons[75].click()
        self.assertEqual(page.slider_vol.value(), 75)
        self.assertEqual(page.lbl_vol.text(), "ГРОМКОСТЬ: 75%")
        self.mock_actions.set_master_volume.assert_called_with(75)

        # Move slider to non-multiple e.g. 33 -> snaps to 25
        page.slider_vol.setValue(33)
        self.assertEqual(page.slider_vol.value(), 25)
        self.assertEqual(page.lbl_vol.text(), "ГРОМКОСТЬ: 25%")

    def test_visual_tab_page_creation_and_screens(self) -> None:
        page = VisualTabPage(self.mock_window)
        self.assertIsNotNone(page)
        self.assertTrue(hasattr(page, "combo_screen"))

    def test_system_tab_page_creation(self) -> None:
        page = SystemTabPage(self.mock_window)
        self.assertIsNotNone(page)
        page._set_reminder_range(60_000, 300_000)
        self.mock_actions.set_reminder_interval_range.assert_called_with(60_000, 300_000)

        page.btn_halt.click()
        self.mock_window.close.assert_called()


if __name__ == "__main__":
    unittest.main()
