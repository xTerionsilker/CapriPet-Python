"""Сервис распознавания речи с поддержкой бэкендов Vosk и Faster-Whisper."""

from __future__ import annotations

import enum
import importlib
import importlib.metadata
import json
import logging
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None  # type: ignore[assignment]

try:
    import vosk
except ImportError:
    vosk = None  # type: ignore[assignment]

from ..core.settings import get_config_value, set_config_value

logger = logging.getLogger(__name__)


class RecognitionError(RuntimeError):
    """Исключение при ошибках загрузки моделей или распознавания речи."""


class ModelStatus(enum.Enum):
    """Статусы жизненного цикла модели распознавания речи."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"


class SpeechRecognitionBackend:
    """Базовый интерфейс для бэкендов распознавания речи."""

    def is_available(self) -> bool:
        raise NotImplementedError

    def get_model(self) -> Any:
        raise NotImplementedError

    def recognize(
        self, data: bytes, *, channels: int, sample_rate: int
    ) -> str | None:
        raise NotImplementedError


class FasterWhisperBackend(SpeechRecognitionBackend):
    """Бэкенд распознавания речи на базе Faster-Whisper."""

    def __init__(
        self, model_size: str = "base", compute_type: str = "int8"
    ) -> None:
        self.model_size = model_size
        self.compute_type = compute_type
        self._model: Any = None
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        if sys.modules.get("faster_whisper") is None:
            return False
        self._available = WhisperModel is not None
        return self._available

    def _find_model_path(self) -> str:
        project_root = Path(__file__).resolve().parents[2]
        local_base = project_root / "models" / "whisper-base"
        if (local_base / "model.bin").exists():
            return str(local_base)
        return self.model_size

    def get_model(self) -> Any:
        if self._model is not None:
            return self._model
        if WhisperModel is None:
            raise RecognitionError(
                "Для Faster-Whisper установите библиотеку: pip install faster-whisper"
            )

        path = self._find_model_path()
        logger.info(
            "Загрузка модели Faster-Whisper (%s, %s)...",
            path,
            self.compute_type,
        )
        self._model = WhisperModel(
            path,
            device="cpu",
            compute_type=self.compute_type,
            cpu_threads=2,
        )
        return self._model

    def _get_model(self) -> Any:
        return self.get_model()

    def recognize(
        self, data: bytes, *, channels: int, sample_rate: int
    ) -> str | None:
        if not self.is_available() or np is None:
            return None

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

        model = self.get_model()
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


class VoskSpeechService:
    """Управление моделями Vosk и Faster-Whisper и диспетчеризация распознавания речи."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._status = ModelStatus.UNLOADED
        self._vosk_model: Any = None
        self._preload_thread: threading.Thread | None = None
        self._recognizers: dict[int, Any] = {}
        self._whisper_backend: Any = None

    def get_backend(self) -> str:
        backend = str(
            get_config_value("audio.asr_backend", "vosk")
        ).lower()
        return "whisper" if backend == "whisper" else "vosk"

    def set_backend(self, backend: str) -> None:
        target = "whisper" if backend.lower() == "whisper" else "vosk"
        set_config_value("audio.asr_backend", target)
        logger.info("Бэкенд распознавания речи переключен на: %s", target)
        with self._lock:
            return self._status

    @property
    def status(self) -> ModelStatus:
        with self._lock:
            return self._status

    @property
    def is_ready(self) -> bool:
        backend = self.get_backend()
        with self._lock:
            if backend == "whisper":
                return (
                    self._whisper_backend is not None
                    and getattr(self._whisper_backend, "_model", None)
                    is not None
                )
            return (
                self._status == ModelStatus.READY
                and self._vosk_model is not None
            )

    @property
    def is_loading(self) -> bool:
        with self._lock:
            return self._status == ModelStatus.LOADING

    @property
    def load_failed(self) -> bool:
        with self._lock:
            return self._status == ModelStatus.FAILED

    def check_available(self) -> None:
        backend = self.get_backend()
        if backend == "whisper":
            if WhisperModel is None:
                raise RecognitionError(
                    "Для Faster-Whisper установите библиотеку: pip install faster-whisper"
                )
            return

        if vosk is None:
            raise RecognitionError(
                "Для локального голосового ввода установите vosk (pip install vosk)."
            )

    def find_model_path(self) -> str | None:
        env_path = os.environ.get("CAPRI_VOSK_MODEL")
        if env_path:
            path = Path(env_path).expanduser().resolve()
            if path.exists():
                return str(path)

        project_root = Path(__file__).resolve().parents[2]
        models_dir = project_root / "models"
        if models_dir.exists():
            for candidate in sorted(models_dir.glob("vosk-model*")):
                if candidate.is_dir():
                    return str(candidate)

        cache_dir = Path.home() / ".cache" / "vosk"
        if cache_dir.exists():
            for candidate in sorted(cache_dir.glob("vosk-model*")):
                if candidate.is_dir():
                    return str(candidate)

        return None

    def get_model_info(self) -> dict[str, object]:
        backend = self.get_backend()
        if backend == "whisper":
            whisper_available = WhisperModel is not None
            wb = self._whisper_backend
            initialized = (
                wb is not None and getattr(wb, "_model", None) is not None
            )
            return {
                "backend": "whisper",
                "available": whisper_available,
                "initialized": initialized,
                "loading": False,
                "failed": False,
                "model_name": "whisper-base",
                "model_version": "base",
                "vosk_version": "",
            }

        vosk_available = vosk is not None
        vosk_version = ""
        if vosk is not None:
            vosk_version = str(getattr(vosk, "__version__", "") or "")
            if not vosk_version:
                try:
                    vosk_version = importlib.metadata.version("vosk")
                except Exception:
                    vosk_version = ""

        model_path = self.find_model_path()
        model_name = Path(model_path).name if model_path else ""
        model_version = ""
        if model_name:
            match = re.search(r"(\d+(?:\.\d+)+)", model_name)
            if match:
                model_version = match.group(1)

        with self._lock:
            return {
                "available": vosk_available,
                "initialized": self._vosk_model is not None,
                "loading": self._status == ModelStatus.LOADING,
                "failed": self._status == ModelStatus.FAILED,
                "model_name": model_name,
                "model_version": model_version,
                "vosk_version": vosk_version,
            }

    def preload_async(self) -> None:
        with self._lock:
            if self._vosk_model is not None:
                return
            if (
                self._preload_thread is not None
                and self._preload_thread.is_alive()
            ):
                return
            self._preload_thread = threading.Thread(
                target=self._preload_worker,
                name="capri-vosk-preload",
                daemon=True,
            )
            self._preload_thread.start()

    def _preload_worker(self) -> None:
        try:
            if self.get_backend() == "whisper":
                backend = self.get_whisper_backend()
                backend.get_model()
            else:
                self.get_model()
        except RecognitionError as error:
            logger.warning(
                "Не удалось прогреть модель распознавания: %s", error
            )
        except Exception:
            logger.exception(
                "Ошибка фоновой загрузки модели распознавания."
            )

    def get_whisper_backend(self) -> FasterWhisperBackend:
        with self._lock:
            if self._whisper_backend is None:
                self._whisper_backend = FasterWhisperBackend()
            return self._whisper_backend

    def get_model(self) -> Any:
        with self._lock:
            if self._vosk_model is not None:
                return self._vosk_model

            self._status = ModelStatus.LOADING
            if vosk is None:
                self._status = ModelStatus.FAILED
                raise RecognitionError(
                    "Для локального распознавания установите vosk (pip install vosk)."
                )

            vosk.SetLogLevel(-1)
            model_path = self.find_model_path()
            try:
                if model_path:
                    self._vosk_model = vosk.Model(model_path)
                else:
                    self._vosk_model = vosk.Model(lang="ru")
                self._status = ModelStatus.READY
                return self._vosk_model
            except Exception as error:
                self._status = ModelStatus.FAILED
                raise RecognitionError(
                    "Не удалось загрузить модель Vosk. Убедитесь, что модель для русского языка "
                    "скачана в папку models/ (например, models/vosk-model-small-ru-0.22)."
                ) from error

    @staticmethod
    def to_mono(data: bytes, channels: int) -> bytes:
        if channels <= 1 or np is None:
            return data

        samples = np.frombuffer(data, dtype=np.int16)
        frame_count = samples.size // channels
        if frame_count == 0:
            return b""
        frames = samples[: frame_count * channels].reshape(
            frame_count, channels
        )
        return (
            frames.mean(axis=1, dtype=np.float32)
            .astype(np.int16)
            .tobytes()
        )

    def create_recognizer(
        self, sample_rate: int, grammar: str | None = None
    ) -> Any:
        if vosk is None:
            raise RecognitionError(
                "Для локального распознавания установите vosk (pip install vosk)."
            )

        model = self.get_model()
        if grammar:
            return vosk.KaldiRecognizer(model, float(sample_rate), grammar)
        return vosk.KaldiRecognizer(model, float(sample_rate))

    def recognize(
        self, data: bytes, *, channels: int, sample_rate: int
    ) -> str | None:
        if self.get_backend() == "whisper":
            backend = self.get_whisper_backend()
            return backend.recognize(
                data, channels=channels, sample_rate=sample_rate
            )

        if vosk is None:
            return None

        model = self.get_model()
        mono_data = self.to_mono(data, channels)

        with self._lock:
            rec = self._recognizers.get(sample_rate)
            if rec is None:
                rec = vosk.KaldiRecognizer(model, float(sample_rate))
                self._recognizers[sample_rate] = rec
            else:
                reset = getattr(rec, "Reset", None)
                if reset is not None:
                    reset()
                else:
                    rec = vosk.KaldiRecognizer(model, float(sample_rate))
                    self._recognizers[sample_rate] = rec

            rec.AcceptWaveform(mono_data)
            result = json.loads(rec.FinalResult())

        text = result.get("text", "").strip()
        return text or None


_service = VoskSpeechService()


def get_backend() -> str:
    return _service.get_backend()


def set_backend(backend: str) -> None:
    _service.set_backend(backend)


def check_available() -> None:
    _service.check_available()


def get_model_info() -> dict[str, object]:
    return _service.get_model_info()


def is_model_ready() -> bool:
    return _service.is_ready


def is_model_loading() -> bool:
    return _service.is_loading


def model_load_failed() -> bool:
    return _service.load_failed


def preload_model_async() -> None:
    _service.preload_async()


def get_vosk_model() -> Any:
    return _service.get_model()


def create_recognizer(sample_rate: int, grammar: str | None = None) -> Any:
    return _service.create_recognizer(sample_rate, grammar=grammar)


def to_mono(data: bytes, channels: int) -> bytes:
    return _service.to_mono(data, channels)


def recognize(
    data: bytes, *, channels: int, sample_rate: int
) -> str | None:
    return _service.recognize(
        data, channels=channels, sample_rate=sample_rate
    )
