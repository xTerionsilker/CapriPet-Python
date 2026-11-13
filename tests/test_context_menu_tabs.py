"""Тесты модульных страниц вкладок киберпанк-контекстного меню."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QCheckBox

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

        page.btn_breach.click()
        self.mock_actions.trigger_intro_breach.assert_called()

    def test_system_tab_page_creation(self) -> None:
        page = SystemTabPage(self.mock_window)
        self.assertIsNotNone(page)
        self.assertTrue(hasattr(page, "chk_reminders"))
        self.assertTrue(hasattr(page, "chk_game"))
        self.assertTrue(hasattr(page, "chk_process_monitoring"))
        self.assertFalse(hasattr(page, "chk_discord"))
        self.assertTrue(hasattr(page, "chk_shredder"))
        self.assertEqual(len(page._timeout_buttons), 3)

        # Toggle process monitoring
        page.chk_process_monitoring.setChecked(False)
        self.mock_actions.set_process_monitoring_enabled.assert_called_with(False)

        # Click a frequency preset
        preset_key = "Часто (1 – 5 мин)"
        self.assertIn(preset_key, page._freq_buttons)
        page._freq_buttons[preset_key].click()
        self.mock_actions.set_reminder_interval_range.assert_called_with(60_000, 300_000)

        page.btn_halt.click()
        self.mock_window.close.assert_called()

    def test_system_tab_page_halt_closes_parent_dialog(self) -> None:
        from PySide6.QtWidgets import QDialog

        parent_dialog = QDialog()
        parent_dialog.close = MagicMock()
        page = SystemTabPage(self.mock_window, parent_dialog)
        page.btn_halt.click()
        parent_dialog.close.assert_called_with(immediate=True)
        self.mock_window.close.assert_called()


    def test_audio_tab_page_no_duplicate_volume_hud(self) -> None:
        page = AudioTabPage(self.mock_window)
        vol_hud_checkboxes = [
            cb for cb in page.findChildren(QCheckBox) if "Volume HUD" in cb.text()
        ]
        self.assertEqual(len(vol_hud_checkboxes), 1)

    @patch("capri.ui.context_menu_tabs.get_speech_sfx")
    def test_ui_sound_effects_triggered(self, mock_get_sfx: MagicMock) -> None:
        mock_sfx = MagicMock()
        mock_get_sfx.return_value = mock_sfx

        core_page = CoreTabPage(self.mock_window)
        mock_sfx.play_relay_snap.reset_mock()
        core_page.btn_summon.click()
        mock_sfx.play_relay_snap.assert_called()

        core_page.btn_deck.click()
        mock_sfx.play_relay_snap.assert_called()

        core_page.btn_teleport.click()
        mock_sfx.play_relay_snap.assert_called()

        core_page.btn_reset_pos.click()
        mock_sfx.play_relay_snap.assert_called()

        audio_page = AudioTabPage(self.mock_window)
        mock_sfx.play_relay_snap.reset_mock()
        audio_page._preset_buttons[50].click()
        mock_sfx.play_relay_snap.assert_called()

        visual_page = VisualTabPage(self.mock_window)
        mock_sfx.play_relay_snap.reset_mock()
        visual_page._scale_buttons[100].click()
        mock_sfx.play_relay_snap.assert_called()

        system_page = SystemTabPage(self.mock_window)
        mock_sfx.play_relay_snap.reset_mock()
        system_page._timeout_buttons[5].click()
        mock_sfx.play_relay_snap.assert_called()


if __name__ == "__main__":
    unittest.main()
