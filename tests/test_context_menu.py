from __future__ import annotations

import sys
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from capri.ui.context_menu import ContextMenuBuilder, ReminderRangeDialog


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

    def test_context_menu_builder_quick_actions_at_top(self) -> None:
        class DummyWindow:
            def __init__(self) -> None:
                self._orchestrator = None
                self.glitches_enabled = False
                self.reminders_enabled = True

            def get_designated_screen(self) -> None:
                return None

            def close(self) -> None:
                pass

        builder = ContextMenuBuilder(DummyWindow())
        menu = builder.build(for_tray=False)
        action_texts = [act.text() for act in menu.actions() if not act.isSeparator()]

        self.assertIn("DISCORD", action_texts[1])
        self.assertIn("VOICE", action_texts[2])
        self.assertIn("GLITCH", action_texts[3])

