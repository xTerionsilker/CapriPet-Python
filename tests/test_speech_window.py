import os
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from capri.ui.speech import SpeechWindow, CyberHudBubble, show_text, close_all

_app = QApplication.instance() or QApplication([])


class TestSpeechWindow(unittest.TestCase):

    def test_bubble_paint(self):
        bubble = CyberHudBubble(title="[TEST://NET_LINK]")
        bubble.resize(300, 150)
        bubble.set_title("[TEST://NEW_TITLE]")
        self.assertEqual(bubble._title, "[TEST://NEW_TITLE]")
        # Отрисовка в буфер
        pixmap = bubble.grab()
        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.width(), 300)
        self.assertEqual(pixmap.height(), 150)

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

        w.close()

    def test_scramble_and_cursor(self):
        w = show_text("Hello\nWorld Hacker!", chars_per_second=100.0)
        w._start_message()

        # Тестируем рендер скрембла
        w._render_scramble(5)
        text_html = w._label.text()
        # Должен быть циан (#00f0ff) для первых 5 символов "Hello"
        self.assertIn("#00f0ff", text_html)
        self.assertIn("Hello", text_html)
        # Должна быть каретка █
        self.assertIn("█", text_html)
        # Должен сохраняться перевод строки <br>
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

        w.close()

    def test_skip_click_behavior(self):
        w = show_text("Double click test", chars_per_second=100.0)
        # 1. Клик во время transmitting раскрывает весь текст
        w.skip()
        self.assertTrue(w.is_finished)
        self.assertEqual(w._phase, "holding")
        self.assertFalse(w._transmit_timer.isActive())

        # 2. Клик в состоянии holding закрывает окно
        w.skip()
        self.assertFalse(w.isVisible())

    def test_close_all(self):
        w1 = show_text("Text 1")
        w2 = show_text("Text 2")
        close_all()


if __name__ == "__main__":
    unittest.main()
