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
        # Отрисовка в буфер
        pixmap = bubble.grab()
        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.width(), 300)
        self.assertEqual(pixmap.height(), 150)

    def test_speech_window_creation_and_skip(self):
        w = show_text("Hello cyberpunk world!", chars_per_second=100.0)
        self.assertIsInstance(w, SpeechWindow)
        self.assertEqual(w.text, "Hello cyberpunk world!")
        self.assertFalse(w.is_finished)

        # Проверяем первый skip (мгновенное завершение показа текста)
        w.skip()
        self.assertTrue(w.is_finished)

        # Проверяем второй skip (закрытие окна)
        w.skip()

    def test_close_all(self):
        w1 = show_text("Text 1")
        w2 = show_text("Text 2")
        close_all()


if __name__ == "__main__":
    unittest.main()
