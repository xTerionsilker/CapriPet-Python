from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from capri.ui.speech_bubble import CyberHudBubble


class TestSpeechBubble(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_cyber_hud_bubble_init(self) -> None:
        bubble = CyberHudBubble(title="[NET_LINK://TEST]", chamfer=14)
        self.assertEqual(bubble._title, "[NET_LINK://TEST]")
        self.assertEqual(bubble._chamfer, 14)
        self.assertEqual(bubble.anim_phase, "opening")

    def test_cyber_hud_bubble_setters(self) -> None:
        bubble = CyberHudBubble()
        bubble.set_title("[OVERRIDE]")
        self.assertEqual(bubble._title, "[OVERRIDE]")
        bubble.set_pointer_direction("right")
        self.assertEqual(bubble._pointer_direction, "right")
        bubble.set_excited(True)
        self.assertTrue(bubble._is_excited)
