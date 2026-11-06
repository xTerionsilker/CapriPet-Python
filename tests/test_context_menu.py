from __future__ import annotations

import sys
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from capri.ui.context_menu import ReminderRangeDialog


class TestContextMenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication(sys.argv)

    def test_reminder_range_dialog_creation_and_bounds(self) -> None:
        dlg = ReminderRangeDialog(init_min=10, init_max=60)
        flags = dlg.windowFlags()
        self.assertTrue(bool(flags & Qt.WindowType.FramelessWindowHint))
        self.assertEqual(dlg.spin_from.value(), 10)
        self.assertEqual(dlg.spin_to.value(), 60)

        dlg.spin_from.setValue(80)
        self.assertGreaterEqual(dlg.spin_to.value(), 80)

        dlg.spin_to.setValue(20)
        self.assertLessEqual(dlg.spin_from.value(), 20)
