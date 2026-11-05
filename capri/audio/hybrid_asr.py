from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SpeechRecognitionBackend:
    """Базовый абстрактный интерфейс для бэкендов распознавания речи."""

    def is_available(self) -> bool:
        raise NotImplementedError

    def recognize(self, data: bytes, *, channels: int, sample_rate: int) -> str | None:
        raise NotImplementedError


class FasterWhisperBackend(SpeechRecognitionBackend):
\
\
\
\


    def __init__(self, model_size: str = "base", compute_type: str = "int8") -> None:
        self.model_size = model_size
        self.compute_type = compute_type
        self._model: Any = None
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import faster_whisper
            self._available = True
        except ImportError:
            self._available = False
        return self._available

    def _find_model_path(self) -> str:
        project_root = Path(__file__).resolve().parents[2]
        local_base = project_root / "models" / "whisper-base"
        if (local_base / "model.bin").exists():
            return str(local_base)
        return self.model_size

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        from faster_whisper import WhisperModel
        path = self._find_model_path()
        logger.info("Загрузка модели Faster-Whisper (%s, %s)...", path, self.compute_type)
        self._model = WhisperModel(path, device="cpu", compute_type=self.compute_type, cpu_threads=2)
        return self._model

    def recognize(self, data: bytes, *, channels: int, sample_rate: int) -> str | None:
        if not self.is_available():
            return None
        import numpy as np

        samples = np.frombuffer(data, dtype=np.int16)
        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)
        audio = samples.astype(np.float32) / 32768.0

        if sample_rate != 16000 and len(audio) > 0:
            target_len = int(len(audio) * 16000 / sample_rate)
            audio = np.interp(
                np.linspace(0, len(audio), target_len, endpoint=False),
                np.arange(len(audio)),
                audio,
            ).astype(np.float32)

        model = self._get_model()
        segments, _ = model.transcribe(
            audio,
            beam_size=1,
            initial_prompt="Капри, Capri, открой, включи, спотифай, Spotify, ютуб, YouTube, пауза, громкость, статус.",
            condition_on_previous_text=False,
            vad_filter=False,
            no_speech_threshold=0.6,
        )
        text = " ".join(seg.text for seg in segments).strip()
        return text or None
