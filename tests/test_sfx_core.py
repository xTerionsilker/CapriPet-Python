from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from capri.audio.sfx_core import (
    DEFAULT_SAMPLE_RATE,
    to_pcm_16bit,
    write_wav_16bit,
)


class TestSfxCore(unittest.TestCase):
    def test_to_pcm_16bit_clamping_and_saturation(self) -> None:
        packed_zero = to_pcm_16bit(0.0)
        self.assertEqual(len(packed_zero), 2)

        packed_pos = to_pcm_16bit(5.0)
        self.assertEqual(len(packed_pos), 2)

        packed_neg = to_pcm_16bit(-5.0)
        self.assertEqual(len(packed_neg), 2)

        packed_array = to_pcm_16bit(np.zeros(100))
        self.assertEqual(len(packed_array), 200)

    def test_write_wav_16bit_creates_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "test.wav"
            frames = to_pcm_16bit(np.zeros(100))
            write_wav_16bit(wav_path, frames, sample_rate=DEFAULT_SAMPLE_RATE)
            self.assertTrue(wav_path.exists())
            self.assertGreater(wav_path.stat().st_size, 44)  # WAV header is 44 bytes
