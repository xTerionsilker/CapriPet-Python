"""Core mathematical and DSP primitives for procedural audio synthesis."""

from __future__ import annotations

import wave
from collections.abc import Sequence
from pathlib import Path

import numpy as np

DEFAULT_SAMPLE_RATE: int = 44100


def write_wav_16bit(
    file_path: Path,
    frames: bytes | bytearray,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> None:
    """Записывает 16-bit моно PCM WAV файл с атомарным созданием директории."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def to_pcm_16bit(
    signal: float | Sequence[float] | np.ndarray,
    drive: float = 1.0,
    master_gain: float = 0.95,
) -> bytes:
    """Применяет нелинейную сатурацию tanh и преобразует массив в 16-bit PCM байты."""
    arr = np.asarray(signal, dtype=np.float64)
    saturated = np.tanh(arr * drive) * master_gain
    clamped = np.clip(saturated, -1.0, 1.0)
    samples = (clamped * 32767.0).astype(np.int16)
    return samples.tobytes()
