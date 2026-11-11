"""Smoke-тестирование полного жизненного цикла главного окна CapriWindow."""

from __future__ import annotations

import unittest

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication


class TestWindowLifecycleSmoke(unittest.TestCase):
    """Интеграционный Smoke-тест для обнаружения скрытых ошибок атрибутов и ленивых замыканий."""

    @classmethod
    def setUpClass(cls) -> None:
        if QApplication.instance() is None:
            cls._app = QApplication([])
        else:
            cls._app = QApplication.instance()

    def test_capri_window_lifecycle_and_prank_signals(self) -> None:
        """Проверяет запуск окна, вызов стартовых методов, колбэков безопасности и событий ввода."""
        from capri.ui.pet_window import CapriWindow

        window = CapriWindow()
        self.assertIsNotNone(window)

        # 1. Проверка колбэков безопасности координатора пасхалок
        # Ни один из них не должен вызывать AttributeError
        self.assertIsInstance(window.prank_coordinator.can_trigger_prank(), bool)
        self.assertIsInstance(window.prank_coordinator._check_shredding(), bool)
        self.assertIsInstance(window.prank_coordinator._check_recording(), bool)
        self.assertIsInstance(window.prank_coordinator._check_game_active(), bool)

        # 2. Эмуляция полного стартового появления
        window._reveal_on_startup()
        window._on_startup_finished()

        # 3. Эмуляция срабатывания розыгрыша уклонения
        window._on_prank_dodge(2)
        self.assertEqual(window._dodge_hops_remaining, 2)

        # 4. Эмуляция клика мыши на спрайте
        dummy_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(10, 10),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )
        window.mousePressEvent(dummy_event)

        # 5. Проверка Варианта А и Б дампа памяти
        window._on_prank_relic_dump("terminal")
        window._on_prank_relic_dump("bubble")

        # 6. Проверка оверлея тающего экрана
        window._on_prank_melt()

        # 7. Корректное завершение работы
        window.effects.stop_all()
        window.close()
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
