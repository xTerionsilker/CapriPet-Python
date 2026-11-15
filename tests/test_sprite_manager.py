"""Unit tests for SpriteManager with dynamic sprite parsing."""

from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from capri.ui.sprite_manager import SpriteManager


class TestSpriteManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_sprite_manager_initialization(self) -> None:
        manager = SpriteManager()
        self.assertGreater(manager.sprite_count, 0)
        self.assertIn(manager.current_sprite_key, manager.sprite_keys)
        self.assertFalse(manager.current_pixmap.isNull())
        self.assertEqual(manager.current_pose, manager.current_sprite_key)

    def test_set_random_sprite(self) -> None:
        manager = SpriteManager()
        if manager.sprite_count > 1:
            initial = manager.current_sprite_key
            # In a few tries, exclude_current should change it
            changed = manager.set_random_sprite(exclude_current=True)
            self.assertTrue(changed)
            self.assertNotEqual(manager.current_sprite_key, initial)
        else:
            self.assertFalse(manager.set_random_sprite(exclude_current=True))

    def test_set_pose_compatibility(self) -> None:
        manager = SpriteManager()
        # set_pose without arguments or with unknown pose picks random
        result = manager.set_pose("unknown_pose")
        self.assertIn(manager.current_sprite_key, manager.sprite_keys)
        self.assertIsInstance(result, bool)

        # set_pose with specific valid key
        first_key = manager.sprite_keys[0]
        manager.set_pose(first_key)
        self.assertEqual(manager.current_sprite_key, first_key)

    def test_set_sprite_scale(self) -> None:
        manager = SpriteManager()
        current = manager.scale_percent
        target = 125 if current != 125 else 100
        self.assertTrue(manager.set_sprite_scale(target))
        self.assertEqual(manager.scale_percent, target)
        # Setting same scale returns False
        self.assertFalse(manager.set_sprite_scale(target))
        # Setting invalid scale returns False
        self.assertFalse(manager.set_sprite_scale(999))
        # Restore original
        manager.set_sprite_scale(current)

    def test_is_point_on_sprite(self) -> None:
        manager = SpriteManager()
        # Out of bounds should return False
        self.assertFalse(manager.is_point_on_sprite(-10, -10))
        self.assertFalse(manager.is_point_on_sprite(9999, 9999))


if __name__ == "__main__":
    unittest.main()
