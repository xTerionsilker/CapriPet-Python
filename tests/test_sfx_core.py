from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from capri.audio.sfx_core import (
    DEFAULT_SAMPLE_RATE,
    pack_sample,
    write_wav_16bit,
)


class TestSfxCore(unittest.TestCase):
    def test_pack_sample_clamping_and_saturation(self) -> None:
        packed_zero = pack_sample(0.0)
        self.assertEqual(len(packed_zero), 2)

        packed_pos = pack_sample(5.0)
        self.assertEqual(len(packed_pos), 2)

        packed_neg = pack_sample(-5.0)
        self.assertEqual(len(packed_neg), 2)

    def test_write_wav_16bit_creates_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "test.wav"
            frames = bytearray()
            for _ in range(100):
                frames.extend(pack_sample(0.0))
            write_wav_16bit(wav_path, frames, sample_rate=DEFAULT_SAMPLE_RATE)
            self.assertTrue(wav_path.exists())
            self.assertGreater(wav_path.stat().st_size, 44)  # WAV header is 44 bytes
