import os
import unittest
from pathlib import Path
import tempfile
import time
import wave

# Устанавливаем offscreen для headless тестов
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from capri.ui.speech_sfx import (
    _generate_swoosh_wav,
    _generate_chirp_wav,
    SpeechSFX,
    get_speech_sfx,
)

_app = QApplication.instance() or QApplication([])


class TestSpeechSFX(unittest.TestCase):

    def test_wav_generation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            swoosh_file = tmp_path / "swoosh.wav"
            chirp_file = tmp_path / "chirp.wav"

            _generate_swoosh_wav(swoosh_file)
            _generate_chirp_wav(chirp_file)

            self.assertTrue(swoosh_file.exists())
            self.assertTrue(chirp_file.exists())

            with wave.open(str(swoosh_file), "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), 44100)
                self.assertGreater(wf.getnframes(), 0)

            with wave.open(str(chirp_file), "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), 44100)
                self.assertGreater(wf.getnframes(), 0)

    def test_sfx_singleton_and_controls(self):
        sfx = get_speech_sfx()
        self.assertIsInstance(sfx, SpeechSFX)
        self.assertIs(sfx, get_speech_sfx())

        # Test volume control
        sfx.set_volume(0.8)
        self.assertAlmostEqual(sfx.get_volume(), 0.8)
        sfx.set_volume(1.5)
        self.assertAlmostEqual(sfx.get_volume(), 1.0)
        sfx.set_volume(-0.5)
        self.assertAlmostEqual(sfx.get_volume(), 0.0)

        # Test enable/mute
        sfx.set_enabled(True)
        self.assertTrue(sfx.is_enabled())
        sfx.set_enabled(False)
        self.assertFalse(sfx.is_enabled())
        sfx.set_enabled(True)

    def test_playback_calls_and_throttling(self):
        sfx = SpeechSFX()
        sfx.set_enabled(True)

        # Swoosh playback
        sfx.play_swoosh()

        # Chirp playback with throttling
        t0 = sfx._last_chirp_time
        sfx.play_chirp()
        t1 = sfx._last_chirp_time
        self.assertGreater(t1, t0)

        # Immediate chirp call should be throttled (no timestamp change)
        sfx.play_chirp()
        self.assertEqual(sfx._last_chirp_time, t1)

        # After waiting > interval, chirp should play
        time.sleep(0.05)
        sfx.play_chirp()
        self.assertGreater(sfx._last_chirp_time, t1)


if __name__ == "__main__":
    unittest.main()
