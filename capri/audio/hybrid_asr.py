from __future__ import annotations

import logging
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


    def __init__(self, model_size: str = "tiny", compute_type: str = "int8") -> None:
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

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        from faster_whisper import WhisperModel
        logger.info("Загрузка модели Faster-Whisper (%s, %s)...", self.model_size, self.compute_type)
        self._model = WhisperModel(self.model_size, device="cpu", compute_type=self.compute_type)
        return self._model

    def recognize(self, data: bytes, *, channels: int, sample_rate: int) -> str | None:
        if not self.is_available():
            return None
        import io
        import wave


        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(data)
        wav_buf.seek(0)

        model = self._get_model()
        segments, _ = model.transcribe(wav_buf, language="ru", beam_size=1)
        text = " ".join(seg.text for seg in segments).strip()
        return text or None
