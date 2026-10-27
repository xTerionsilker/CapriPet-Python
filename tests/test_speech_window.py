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

    def test_skip_during_transmitting(self):
        w = show_text("Immediate skip message", chars_per_second=100.0)
        self.assertEqual(w._phase, "transmitting")

        # Клик во время фазы transmitting должен мгновенно раскрыть сообщение
        w.skip()
        self.assertTrue(w.is_finished)
        self.assertFalse(w._transmit_timer.isActive())

        # Повторный клик закрывает окно
        w.skip()

    def test_close_all(self):
        w1 = show_text("Text 1")
        w2 = show_text("Text 2")
        close_all()


if __name__ == "__main__":
    unittest.main()
