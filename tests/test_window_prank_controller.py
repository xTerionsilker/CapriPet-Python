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
