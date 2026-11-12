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

        # Test quick toggles
        self.assertTrue(hasattr(page, "chk_discord"))
        page.chk_discord.setChecked(False)
        self.mock_actions.set_discord_enabled.assert_called_with(False)

        self.assertTrue(hasattr(page, "chk_voice"))
        page.chk_voice.setChecked(False)
        self.mock_actions.toggle_voice.assert_called()

        self.assertTrue(hasattr(page, "chk_glitches"))
        page.chk_glitches.setChecked(False)
        self.mock_actions.toggle_glitches.assert_called()

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

        # Test SFX toggles
        self.assertTrue(hasattr(page, "chk_speech"))
        self.assertTrue(hasattr(page, "chk_fx"))
        self.assertTrue(hasattr(page, "combo_mic"))

    def test_visual_tab_page_creation_and_screens(self) -> None:
        page = VisualTabPage(self.mock_window)
        self.assertIsNotNone(page)
        self.assertTrue(hasattr(page, "combo_screen"))
        self.assertTrue(hasattr(page, "btn_breach"))
        self.assertEqual(len(page._scale_buttons), 5)
        self.assertEqual(len(page._glitch_buttons), 3)

    def test_system_tab_page_creation(self) -> None:
        page = SystemTabPage(self.mock_window)
        self.assertIsNotNone(page)
        self.assertTrue(hasattr(page, "chk_reminders"))
        self.assertTrue(hasattr(page, "chk_game"))
        self.assertTrue(hasattr(page, "chk_discord"))
        self.assertTrue(hasattr(page, "chk_shredder"))
        self.assertEqual(len(page._timeout_buttons), 3)

        # Click a frequency preset
        preset_key = "Часто (1 – 5 мин)"
        self.assertIn(preset_key, page._freq_buttons)
        page._freq_buttons[preset_key].click()
        self.mock_actions.set_reminder_interval_range.assert_called_with(60_000, 300_000)

        page.btn_halt.click()
        self.mock_window.close.assert_called()


if __name__ == "__main__":
    unittest.main()
