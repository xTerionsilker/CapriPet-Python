"""Интеграционные тесты вызова 16:9 кибер-меню из окна питомца и трея."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from capri.ui.pet_window_actions import PetWindowActionDelegate
from capri.ui.tray_manager import TrayManager


class TestContextMenuIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.mock_window = MagicMock()
        self.mock_orchestrator = MagicMock()
        self.mock_inactivity = MagicMock()
        self.mock_orchestrator.inactivity = self.mock_inactivity
        self.mock_window._orchestrator = self.mock_orchestrator

    def test_show_context_menu_spawns_hub(self) -> None:
        actions = PetWindowActionDelegate(self.mock_window)
        with patch(
            "capri.ui.context_menu_window.CyberContextMenuWindow.exec"
        ) as mock_exec:
            actions.show_context_menu(QPoint(100, 100))
            self.mock_inactivity.set_paused.assert_any_call(True)
            self.mock_inactivity.set_paused.assert_any_call(False)
            mock_exec.assert_called_once()

    def test_tray_context_activates_hub(self) -> None:
        tray = TrayManager(self.mock_window)
        with patch.object(tray, "_open_hub") as mock_open:
            tray._on_tray_activated(QSystemTrayIcon.ActivationReason.Context)
            mock_open.assert_called_once()


if __name__ == "__main__":
    unittest.main()
