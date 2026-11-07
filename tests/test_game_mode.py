from __future__ import annotations

import unittest
from unittest.mock import patch

from capri.core.settings import CapriConfig, GameModeConfig
from capri.integrations.game_mode import (
    QUNS_ACCEPTS_NOTIFICATIONS,
    QUNS_RUNNING_D3D_FULL_SCREEN,
    GameModeDetector,
)
from capri.ui.speech import is_speech_suppressed, set_speech_suppressed
from capri.ui.speech_sfx import get_speech_sfx


class TestGameMode(unittest.TestCase):

    def test_config_defaults(self) -> None:
        cfg = CapriConfig()
        self.assertTrue(cfg.game_mode.suppression_enabled)
        self.assertEqual(cfg.game_mode.cooldown_seconds, 3.0)
        self.assertIn("steam.exe", cfg.game_mode.blacklist)
        self.assertIsInstance(cfg.game_mode.whitelist, list)

    def test_speech_suppression_flag(self) -> None:
        set_speech_suppressed(True)
        self.assertTrue(is_speech_suppressed())
        set_speech_suppressed(False)
        self.assertFalse(is_speech_suppressed())

    def test_sfx_suppression(self) -> None:
        sfx = get_speech_sfx()
        sfx.set_suppressed(True)
        self.assertFalse(sfx.is_enabled())
        sfx.set_suppressed(False)
        self.assertTrue(sfx.is_enabled())
    @patch("capri.integrations.game_mode.query_user_notification_state")
    def test_detector_state_transition(self, mock_state) -> None:
        mock_state.return_value = QUNS_RUNNING_D3D_FULL_SCREEN
        detector = GameModeDetector(suppression_enabled=True, cooldown_seconds=0.1)

        states: list[bool] = []
        detector.game_mode_changed.connect(states.append)

        detector._check_state()
        self.assertTrue(detector.is_game_active)
        self.assertEqual(states, [True])

        mock_state.return_value = QUNS_ACCEPTS_NOTIFICATIONS
        detector._check_state()
        self.assertTrue(detector.is_game_active)

        detector._on_cooldown_expired()
        self.assertFalse(detector.is_game_active)
        self.assertEqual(states, [True, False])
