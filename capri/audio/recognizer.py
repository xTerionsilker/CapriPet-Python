from __future__ import annotations

import enum
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RecognitionError(RuntimeError):
    pass


class ModelStatus(enum.Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"


class VoskSpeechService:
    """Инкапсулированный сервис распознавания речи Vosk с управлением состояниями и потокобезопасностью."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._status = ModelStatus.UNLOADED
        self._vosk_model: Any = None
        self._preload_thread: threading.Thread | None = None
        self._recognizers: dict[int, Any] = {}

    @property
    def status(self) -> ModelStatus:
        with self._lock:
            return self._status

    @property
    def is_ready(self) -> bool:
        with self._lock:
            return self._status == ModelStatus.READY and self._vosk_model is not None

    @property
    def is_loading(self) -> bool:
        with self._lock:
            return self._status == ModelStatus.LOADING

    @property
    def load_failed(self) -> bool:
        with self._lock:
            return self._status == ModelStatus.FAILED

    def check_available(self) -> None:
        try:
            import importlib

            importlib.import_module("vosk")
        except ImportError as error:
            raise RecognitionError(
                "Для локального голосового ввода установите vosk (pip install vosk)."
            ) from error

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
        vosk_available = True
        vosk_version = ""
        try:
            import vosk

            vosk_version = str(getattr(vosk, "__version__", "") or "")
            if not vosk_version:
                try:
                    from importlib.metadata import version as package_version

                    vosk_version = package_version("vosk")
                except Exception:
                    vosk_version = ""
        except ImportError:
            vosk_available = False

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
            if self._preload_thread is not None and self._preload_thread.is_alive():
                return
            self._preload_thread = threading.Thread(
                target=self._preload_worker,
                name="capri-vosk-preload",
                daemon=True,
            )
            self._preload_thread.start()

    def _preload_worker(self) -> None:
        try:
            self.get_model()
        except RecognitionError as error:
            logger.warning("Не удалось прогреть модель Vosk: %s", error)
        except Exception:
            logger.exception("Ошибка фоновой загрузки модели Vosk.")

    def get_model(self) -> Any:
        with self._lock:
            if self._vosk_model is not None:
                return self._vosk_model

            self._status = ModelStatus.LOADING
            try:
                import vosk
            except ImportError as error:
                self._status = ModelStatus.FAILED
                raise RecognitionError(
                    "Для локального распознавания установите vosk (pip install vosk)."
                ) from error

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
        if channels <= 1:
            return data

        import numpy as np

        samples = np.frombuffer(data, dtype=np.int16)
        frame_count = samples.size // channels
        if frame_count == 0:
            return b""
        frames = samples[: frame_count * channels].reshape(frame_count, channels)
        return frames.mean(axis=1, dtype=np.float32).astype(np.int16).tobytes()

    def create_recognizer(self, sample_rate: int, grammar: str | None = None) -> Any:
        """Создает новый экземпляр KaldiRecognizer для потоковой обработки."""
        import vosk

        model = self.get_model()
        if grammar:
            return vosk.KaldiRecognizer(model, float(sample_rate), grammar)
        return vosk.KaldiRecognizer(model, float(sample_rate))

    def recognize(self, data: bytes, *, channels: int, sample_rate: int) -> str | None:
        import vosk

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
    return "vosk"


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


def recognize(data: bytes, *, channels: int, sample_rate: int) -> str | None:
    return _service.recognize(data, channels=channels, sample_rate=sample_rate)
