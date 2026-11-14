from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from PySide6.QtCore import QPoint, QRect, QSize

from capri.ui.window_prank_controller import (
    WindowPrankController,
    compute_dodge_position,
)


class TestWindowPrankController(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_window = MagicMock()
        self.mock_window.pos.return_value = QPoint(500, 500)
        self.mock_window.size.return_value = QSize(128, 128)
        self.mock_window.get_designated_screen.return_value = None
        self.mock_coordinator = MagicMock()
        self.controller = WindowPrankController(self.mock_window, self.mock_coordinator)

    def test_compute_dodge_position_clamps_to_screen(self) -> None:
        curr_pos = QPoint(100, 100)
        cursor_pos = QPoint(120, 100)
        screen_rect = QRect(0, 0, 800, 600)
        window_size = QSize(100, 100)
        new_pos = compute_dodge_position(
            curr_pos, cursor_pos, screen_rect, window_size, hop_dist=50
        )
        self.assertTrue(screen_rect.contains(QRect(new_pos, window_size)))

    def test_on_prank_dodge_sets_hops(self) -> None:
        self.controller.handle_prank_dodge(3)
        self.assertEqual(self.controller.dodge_hops_remaining, 3)

    def test_on_prank_melt_calls_effects(self) -> None:
        self.controller.handle_prank_melt()
        self.mock_window._effects.play_melting_screen.assert_called_once()

    def test_on_prank_relic_dump_terminal(self) -> None:
        self.controller.handle_prank_relic_dump("terminal")
        self.mock_window._effects.play_relic_dump_terminal.assert_called_once()

    def test_compute_dodge_position_default_hop_dist_extended(self) -> None:
        curr_pos = QPoint(500, 500)
        cursor_pos = QPoint(520, 500)
        screen_rect = QRect(0, 0, 1920, 1080)
        window_size = QSize(100, 100)
        new_pos = compute_dodge_position(curr_pos, cursor_pos, screen_rect, window_size)
        # При векторе от курсора (520->500) смещение по X влево: dx ~ -hop_dist (~280)
        dist = ((new_pos.x() - curr_pos.x()) ** 2 + (new_pos.y() - curr_pos.y()) ** 2) ** 0.5
        self.assertGreaterEqual(dist, 200.0)

    def test_execute_cursor_dodge_triggers_glitch_orb_teleport(self) -> None:
        self.mock_window.isHidden.return_value = False
        self.mock_window.width.return_value = 128
        self.mock_window.height.return_value = 128
        self.controller.dodge_hops_remaining = 2

        self.controller.execute_cursor_dodge(QPoint(520, 500))
        self.assertEqual(self.controller.dodge_hops_remaining, 1)

        self.mock_window.teleport_controller.teleport_to_point.assert_called_once()
        _, kwargs = self.mock_window.teleport_controller.teleport_to_point.call_args
        self.assertEqual(kwargs.get("mode"), "dodge")
        on_finish = kwargs.get("on_finished_callback")
        self.assertTrue(callable(on_finish))
        on_finish()
        self.mock_window.speak.assert_called_once()

    def test_execute_cursor_dodge_fallback_without_teleport_ctrl(self) -> None:
        self.mock_window.teleport_controller = None
        self.mock_window.width.return_value = 128
        self.mock_window.height.return_value = 128
        self.controller.dodge_hops_remaining = 1

        self.controller.execute_cursor_dodge(QPoint(520, 500))
        self.assertEqual(self.controller.dodge_hops_remaining, 0)
        self.mock_window.move.assert_called_once()
        self.mock_window.speak.assert_called_once()
