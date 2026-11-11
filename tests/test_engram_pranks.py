"""Тесты подсистемы пасхалок и глитч-розыгрышей энграммы (Issue #7)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QCoreApplication


class TestEngramPrankCoordinator(unittest.TestCase):
    """Тестирование ядра координации пасхалок и кулдаунов."""

    @classmethod
    def setUpClass(cls) -> None:
        if QCoreApplication.instance() is None:
            cls._app = QCoreApplication([])
        else:
            cls._app = QCoreApplication.instance()

    def test_engram_prank_cooldown_and_roll(self) -> None:
        from capri.effects.engram_prank_coordinator import EngramPrankCoordinator

        coord = EngramPrankCoordinator(parent=None)
        self.assertTrue(coord.can_trigger_prank())

        coord.arm_cooldown(min_sec=60, max_sec=60)
        self.assertTrue(coord.is_cooldown_active())
        self.assertFalse(coord.can_trigger_prank())

        # Искусственный сброс кулдауна
        coord.clear_cooldown()
        self.assertFalse(coord.is_cooldown_active())
        self.assertTrue(coord.can_trigger_prank())

    def test_safety_gates_suppression(self) -> None:
        from capri.effects.engram_prank_coordinator import EngramPrankCoordinator

        coord = EngramPrankCoordinator(parent=None)

        # Game Mode
        coord.set_game_active_checker(lambda: True)
        self.assertFalse(coord.can_trigger_prank())
        coord.set_game_active_checker(lambda: False)
        self.assertTrue(coord.can_trigger_prank())

        # File Shredder Busy
        coord.set_shredding_checker(lambda: True)
        self.assertFalse(coord.can_trigger_prank())
        coord.set_shredding_checker(lambda: False)
        self.assertTrue(coord.can_trigger_prank())

        # Voice recording busy
        coord.set_recording_checker(lambda: True)
        self.assertFalse(coord.can_trigger_prank())
        coord.set_recording_checker(lambda: False)
        self.assertTrue(coord.can_trigger_prank())

    def test_two_stage_probability_and_anti_repeat(self) -> None:
        from capri.effects.engram_prank_coordinator import EngramPrankCoordinator

        coord = EngramPrankCoordinator(parent=None)
        mock_dodge = MagicMock()
        mock_melt = MagicMock()
        mock_dump = MagicMock()

        coord.sig_trigger_dodge.connect(mock_dodge)
        coord.sig_trigger_melt.connect(mock_melt)
        coord.sig_trigger_relic_dump.connect(mock_dump)

        # 1. Первая ступень: random >= 0.33 -> пасхалка не срабатывает
        with patch("random.random", return_value=0.50):
            triggered = coord.on_pet_appeared()
            self.assertFalse(triggered)
            mock_dodge.assert_not_called()
            mock_melt.assert_not_called()
            mock_dump.assert_not_called()

        # 2. Первая ступень: random < 0.33 -> срабатывает
        with patch("random.random", return_value=0.10):
            with patch("random.choice", return_value="dodge"):
                with patch("random.randint", return_value=3):
                    triggered = coord.on_pet_appeared()
                    self.assertTrue(triggered)
                    mock_dodge.assert_called_once_with(3)
                    self.assertEqual(coord.last_prank, "dodge")
                    self.assertTrue(coord.is_cooldown_active())

        # 3. Анти-повтор: если прошлый был dodge, следующий выбор фильтрует dodge
        coord.clear_cooldown()
        candidates = coord.get_available_prank_types()
        self.assertNotIn("dodge", candidates)
        self.assertIn("melt", candidates)
        self.assertIn("relic_dump", candidates)


if __name__ == "__main__":
    unittest.main()
