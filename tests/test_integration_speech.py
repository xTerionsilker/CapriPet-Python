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
        get_speech_sfx().stop_all()

    def tearDown(self):
        close_all()
        get_speech_sfx().stop_all()

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

        second_window._real_close()

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

        # 2-й клик: закрытие (запуск фазы closing с CRT-глитчем и звуком)
        w.skip()
        self.assertEqual(w._phase, "closing")
        w._real_close()
        self.assertFalse(w.isVisible())

    def test_sfx_stress_and_safety(self):
        """Проверка устойчивости SFX к частым вызовам (троттлинг и безопасность)."""
        sfx = get_speech_sfx()
        # Имитируем сотни частых вызовов дешифратора
        for _ in range(100):
            sfx.play_chirp()
            sfx.play_swoosh()
            sfx.play_close()

        # Глушение и восстановление звука
        sfx.set_enabled(False)
        sfx.play_chirp()
        sfx.play_swoosh()
        sfx.play_close()
        sfx.set_enabled(True)
        sfx.stop_all()

    def test_cyberpunk_full_pipeline(self):
        """Комплексная проверка всех 3 замечаний: звуки, глитч, многострочный динамический текст."""
        lines = [f"NET_COMMAND_{i:02d}: EXECUTE CYBER PROTOCOL DATA STREAM {i}" for i in range(8)]
        text = "\n".join(lines)

        w = show_text(text, chars_per_second=80.0)
        # 1. Фаза transmitting с открывающим глитчем
        self.assertEqual(w._phase, "transmitting")
        self.assertEqual(w._bubble._glitch_mode, "open")
        self.assertGreater(w._estimated_height, 200)

        # 2. Переход к тексту со свушем и дешифровкой
        w._start_message()
        self.assertEqual(w._phase, "typing")
        self.assertIn("█", w._label.text())

        # 3. Дешифровка части текста
        w._tick()
        self.assertTrue(w.isVisible())

        # 4. Фиксация текста
        w._finish()
        self.assertEqual(w._phase, "holding")
        self.assertIn("NET_COMMAND_00", w._label.text())
        self.assertTrue(w._cursor_timer.isActive())

        # 5. Закрытие с глитчем и звуком деактивации
        w.start_close()
        self.assertEqual(w._phase, "closing")
        self.assertEqual(w._bubble._glitch_mode, "close")

        # Отработка остановки глитча и удаление
        w._bubble.stop_glitch()
        self.assertFalse(w._timer.isActive())
        self.assertFalse(w._hold_timer.isActive())


if __name__ == "__main__":
    unittest.main()
