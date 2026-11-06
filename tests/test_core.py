from __future__ import annotations

import unittest

from capri.core.morphology import normalize_spoken_numbers, stem_text
from capri.core.settings import AudioConfig, CapriConfig, WindowConfig, WindowPosition
from capri.core.wake_word import command_after_trigger


class TestCore(unittest.TestCase):
    def test_settings_default(self) -> None:
        cfg = CapriConfig()
        self.assertEqual(cfg.audio.volume, 50)
        self.assertEqual(cfg.audio.asr_backend, "vosk")
        self.assertIsNone(cfg.window.position)

    def test_settings_validation(self) -> None:
        audio = AudioConfig(volume=100)
        self.assertEqual(audio.volume, 100)
        audio_invalid = AudioConfig(volume=80)
        self.assertEqual(audio_invalid.volume, 50)
        win = WindowConfig(position={"x": 100, "y": 200})
        self.assertIsInstance(win.position, WindowPosition)
        self.assertEqual(win.position.x, 100)
        self.assertEqual(win.position.y, 200)

    def test_morphology(self) -> None:
        stemmed = stem_text("капри открой браузер")
        self.assertTrue(len(stemmed) > 0)
        num_converted = normalize_spoken_numbers("пятьдесят пять")
        self.assertIn("55", num_converted)

    def test_wake_word_detection(self) -> None:
        self.assertIsNotNone(command_after_trigger("капри пауза"))
        self.assertIsNotNone(command_after_trigger("каприз стоп"))
        self.assertIsNone(command_after_trigger("привет как дела"))
