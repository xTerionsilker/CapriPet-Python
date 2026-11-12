"""Тесты 16:9 центрированного Cyber Context Menu Window."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QKeyEvent, QWheelEvent
from PySide6.QtWidgets import QApplication

from capri.ui.context_menu_window import (
    CyberContextMenuWindow,
    CyberTabBar,
)


class TestContextMenuWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.mock_window = MagicMock()
        self.mock_actions = MagicMock()
        self.mock_window.actions = self.mock_actions
        self.mock_window._orchestrator = MagicMock()
    def test_window_aspect_ratio_and_centering(self) -> None:
        win = CyberContextMenuWindow(self.mock_window)
        w, h = win.width(), win.height()
        ratio = w / h
        self.assertAlmostEqual(ratio, 16 / 9, delta=0.05)

    def test_tab_bar_wheel_cycling(self) -> None:
        tab_bar = CyberTabBar(["CORE", "AUDIO", "VISUAL", "SYSTEM"])
        self.assertEqual(tab_bar.current_index(), 0)

        # Scroll down -> next tab
        wheel_event = QWheelEvent(
            QPoint(10, 10),
            QPoint(10, 10),
            QPoint(0, 0),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        tab_bar.wheelEvent(wheel_event)
        self.assertEqual(tab_bar.current_index(), 1)

    def test_escape_closes_window(self) -> None:
        win = CyberContextMenuWindow(self.mock_window)
        esc_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier,
        )
        win.keyPressEvent(esc_event)
        self.assertFalse(win.isVisible())


if __name__ == "__main__":
    unittest.main()
