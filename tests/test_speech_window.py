import os
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from capri.ui.speech import CyberHudBubble, show_text, close_all
from capri.ui.speech_sfx import get_speech_sfx

_app = QApplication.instance() or QApplication([])


class TestSpeechWindow(unittest.TestCase):

    def tearDown(self):
        close_all()
        get_speech_sfx().stop_all()

    def test_bubble_paint_and_glitch(self):
        bubble = CyberHudBubble(title="[TEST://NET_LINK]")
        bubble.resize(300, 150)
        bubble.set_title("[TEST://NEW_TITLE]")
        self.assertEqual(bubble._title, "[TEST://NEW_TITLE]")

        # Тест отрисовки без глитча
        pixmap = bubble.grab()
        self.assertFalse(pixmap.isNull())

        # Тест запуска и отрисовки глитча появления
        bubble.start_glitch("open", duration_ms=100)
        self.assertEqual(bubble._glitch_mode, "open")
        self.assertTrue(bubble._glitch_timer.isActive())
        pixmap_glitch = bubble.grab()
        self.assertFalse(pixmap_glitch.isNull())

        # Остановка глитча
        bubble.stop_glitch()
        self.assertIsNone(bubble._glitch_mode)

    def test_two_phase_mechanism(self):
        w = show_text("Cyberpunk dialog message", chars_per_second=100.0)
        self.assertEqual(w._phase, "transmitting")
        self.assertTrue(w._transmit_timer.isActive())
        self.assertTrue(w._transmit_anim_timer.isActive())

        # Проверяем тикер анимации точек
        idx0 = w._transmit_frame_idx
        w._on_transmit_tick()
        self.assertNotEqual(w._transmit_frame_idx, idx0)

        # Переход к сообщению (фаза 2)
        w._start_message()
        self.assertEqual(w._phase, "typing")
        self.assertFalse(w._transmit_timer.isActive())
        self.assertFalse(w._transmit_anim_timer.isActive())
        self.assertTrue(w._timer.isActive())

        w._real_close()

    def test_scramble_and_cursor(self):
        w = show_text("Hello\nWorld Hacker!", chars_per_second=100.0)
        w._start_message()

        # Тестируем рендер скрембла
        w._render_scramble(5)
        text_html = w._label.text()
        self.assertIn("#00f0ff", text_html)
        self.assertIn("Hello", text_html)
        self.assertIn("█", text_html)
        self.assertIn("<br>", text_html)

        # Завершаем дешифровку
        w._finish()
        self.assertTrue(w.is_finished)
        self.assertEqual(w._phase, "holding")
        self.assertTrue(w._cursor_timer.isActive())

        # Проверяем мигание каретки
        cursor_vis = w._cursor_visible
        w._on_cursor_tick()
        self.assertNotEqual(w._cursor_visible, cursor_vis)

        w._real_close()

    def test_skip_and_closing_glitch(self):
        w = show_text("Double click test", chars_per_second=100.0)
        # 1. Клик во время transmitting раскрывает весь текст
        w.skip()
        self.assertTrue(w.is_finished)
        self.assertEqual(w._phase, "holding")
        self.assertFalse(w._transmit_timer.isActive())

        # 2. Клик в состоянии holding запускает фазу closing с глитчем
        w.skip()
        self.assertEqual(w._phase, "closing")
        self.assertEqual(w._bubble._glitch_mode, "close")

        # Принудительное реальное закрытие
        w._real_close()

    def test_multiline_dynamic_height(self):
        """Проверка динамического расчета высоты для длинных многострочных текстов."""
        short_w = show_text("Короткий текст")
        long_text = "\n".join([f"Команда {i}: описание действия и аргументов строки {i}" for i in range(12)])
        long_w = show_text(long_text)

        # Расчетная высота для длинного текста должна быть существенно больше короткого
        self.assertGreater(long_w._estimated_height, short_w._estimated_height)
        self.assertGreater(long_w._estimated_height, 200)

        short_w._real_close()
        long_w._real_close()

    def test_close_all(self):
        show_text("Text 1")
        show_text("Text 2")
        close_all()


if __name__ == "__main__":
    unittest.main()
