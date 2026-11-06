from __future__ import annotations

import sys
import unittest

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from capri.ui.sprite_manager import SpriteManager


class TestSpriteManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication(sys.argv)

    def test_sprite_scale_bounds(self) -> None:
        mgr = SpriteManager()
        self.assertIn(mgr.scale_percent, (50, 75, 100, 125, 150))
        mgr.set_sprite_scale(150)
        self.assertEqual(mgr.scale_percent, 150)
        mgr.set_sprite_scale(999)
        self.assertEqual(mgr.scale_percent, 150)

    def test_is_point_on_sprite_with_transparent_image(self) -> None:
        mgr = SpriteManager()
        img = QImage(10, 10, QImage.Format.Format_ARGB32)
        img.fill(0)
        mgr._cached_hit_image = img
        self.assertFalse(mgr.is_point_on_sprite(5, 5))
        self.assertFalse(mgr.is_point_on_sprite(-1, -1))
