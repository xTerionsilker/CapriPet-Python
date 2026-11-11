"""Core mathematical and DSP primitives for procedural audio synthesis."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

DEFAULT_SAMPLE_RATE: int = 44100


def write_wav_16bit(
    file_path: Path,
    frames: bytearray,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> None:
    """Записывает 16-bit моно PCM WAV файл с атомарным созданием директории."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def pack_sample(val: float, drive: float = 1.0, master_gain: float = 0.95) -> bytes:
    """Применяет нелинейную сатурацию tanh и упаковывает в 16-bit int."""
    saturated = math.tanh(val * drive) * master_gain
    clamped = max(-1.0, min(1.0, saturated))
    sample = int(clamped * 32767.0)
    return struct.pack("<h", max(-32768, min(32767, sample)))
