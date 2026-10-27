import os
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from capri.ui.speech import show_text, close_all
from capri.ui.speech_sfx import get_speech_sfx

_app = QApplication.instance() or QApplication([])


class TestIntegrationSpeech(unittest.TestCase):

    def setUp(self):
        close_all()

    def tearDown(self):
        close_all()

    def test_rapid_speech_interruption(self):
        """Проверка быстрого повторного ввода и перебивания реплики."""
        first_window = show_text("Первая реплика", chars_per_second=50.0)
        self.assertFalse(first_window.is_finished)
        self.assertEqual(first_window._phase, "transmitting")

        # Перебивание второй репликой
        first_window.close()
        second_window = show_text("Вторая реплика, перебившая первую", chars_per_second=50.0)

        self.assertFalse(second_window.is_finished)
        self.assertEqual(second_window._phase, "transmitting")

        # Проверяем, что первая реплика корректно остановила свои таймеры
        self.assertFalse(first_window._transmit_timer.isActive())
        self.assertFalse(first_window._timer.isActive())
        self.assertFalse(first_window._cursor_timer.isActive())

        second_window.close()

    def test_cascade_help_simulation(self):
        """Проверка каскада множественных окон (как в справке _show_help)."""
        windows = []
        for i in range(4):
            w = show_text(f"Команда {i}: описание действия", hold_ms=3000)
            windows.append(w)

        self.assertEqual(len(windows), 4)
        for w in windows:
            self.assertEqual(w._phase, "transmitting")
            self.assertTrue(w.isVisible())

        # Переводим одно окно в сообщение
        windows[0]._start_message()
        self.assertEqual(windows[0]._phase, "typing")

        # Массовое закрытие
        close_all()
        for w in windows:
            self.assertFalse(w._timer.isActive())
            self.assertFalse(w._transmit_timer.isActive())

    def test_full_lifecycle_and_skip(self):
        """Проверка полного цикла: transmitting -> typing -> holding -> close."""
        w = show_text("Киберпанк сообщение для тестирования полного цикла", chars_per_second=200.0)
        self.assertEqual(w._phase, "transmitting")

        # 1-й клик: мгновенный скип передачи и дешифровки
        w.skip()
        self.assertEqual(w._phase, "holding")
        self.assertTrue(w.is_finished)
        self.assertIn("Киберпанк", w._label.text())

        # 2-й клик: закрытие
        w.skip()
        self.assertFalse(w.isVisible())

    def test_sfx_stress_and_safety(self):
        """Проверка устойчивости SFX к частым вызовам (троттлинг и безопасность)."""
        sfx = get_speech_sfx()
        # Имитируем сотни частых вызовов дешифратора
        for _ in range(100):
            sfx.play_chirp()
            sfx.play_swoosh()

        # Глушение и восстановление звука
        sfx.set_enabled(False)
        sfx.play_chirp()
        sfx.play_swoosh()
        sfx.set_enabled(True)


if __name__ == "__main__":
    unittest.main()
