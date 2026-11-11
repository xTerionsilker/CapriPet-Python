from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from capri.ui.window_system_events import WindowSystemEventsHandler


class TestWindowSystemEventsHandler(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_window = MagicMock()
        self.mock_window._closing = False
        self.handler = WindowSystemEventsHandler(self.mock_window)

    def test_on_session_lock_pauses_orchestrator(self) -> None:
        self.handler.handle_session_lock()
        self.mock_window._orchestrator.pause.assert_called_once()
        self.mock_window._glitch_timer.stop.assert_called_once()

    def test_on_session_unlock_resumes_orchestrator(self) -> None:
        self.handler.handle_session_unlock()
        self.mock_window._glitch_timer.start.assert_called_once()
        self.mock_window._orchestrator.resume.assert_called_once()
        self.mock_window.trigger_pose_transition.assert_called_once()

    def test_on_suspend_triggers_fast_terminate_behavior(self) -> None:
        self.handler.handle_system_suspend()
        self.assertTrue(self.mock_window._closing)
        self.mock_window._orchestrator.stop.assert_called_once()
        self.mock_window._effects.stop_all.assert_called_once()
        self.mock_window._glitch_timer.stop.assert_called_once()
        self.mock_window._finalize_quit.assert_called_once()
