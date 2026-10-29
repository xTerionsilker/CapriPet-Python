from __future__ import annotations

import json
import logging
import os
import re
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_vosk_model = None
_model_lock = threading.Lock()
_preload_lock = threading.Lock()
_preload_thread: threading.Thread | None = None
_model_loading = False
_model_failed = False
_recognizers: dict[int, object] = {}
_recognizer_lock = threading.Lock()


class RecognitionError(RuntimeError):
    pass


def get_backend() -> str:
    """Возвращает текущий бэкенд распознавания речи (только локальный vosk)."""
    return "vosk"


def check_available() -> None:
    """Проверяет доступность необходимых зависимостей для распознавания речи."""
    try:
        import importlib

        importlib.import_module("vosk")
    except ImportError as error:
        raise RecognitionError(
            "Для локального голосового ввода установите vosk (pip install vosk)."
        ) from error


def _find_vosk_model_path() -> str | None:
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


def get_model_info() -> dict[str, object]:
    """Возвращает статус локальной модели Vosk без принудительной загрузки."""
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

    model_path = _find_vosk_model_path()
    model_name = Path(model_path).name if model_path else ""
    model_version = ""
    if model_name:
        match = re.search(r"(\d+(?:\.\d+)+)", model_name)
        if match:
            model_version = match.group(1)

    return {
        "available": vosk_available,
        "initialized": _vosk_model is not None,
        "loading": _model_loading,
        "failed": _model_failed,
        "model_name": model_name,
        "model_version": model_version,
        "vosk_version": vosk_version,
    }


def is_model_ready() -> bool:
    return _vosk_model is not None


def is_model_loading() -> bool:
    return _model_loading


def model_load_failed() -> bool:
    return _model_failed


def preload_model_async() -> None:
    """Запускает фоновую загрузку модели Vosk при старте приложения."""
    global _preload_thread
    if _vosk_model is not None:
        return

    with _preload_lock:
        if _vosk_model is not None:
            return
        if _preload_thread is not None and _preload_thread.is_alive():
            return
        _preload_thread = threading.Thread(
            target=_preload_worker,
            name="capri-vosk-preload",
            daemon=True,
        )
        _preload_thread.start()


def _preload_worker() -> None:
    global _model_loading, _model_failed
    _model_loading = True
    _model_failed = False
    try:
        get_vosk_model()
    except RecognitionError as error:
        _model_failed = True
        logger.warning("Не удалось прогреть модель Vosk: %s", error)
    except Exception:
        _model_failed = True
        logger.exception("Ошибка фоновой загрузки модели Vosk.")
    finally:
        _model_loading = False


def get_vosk_model():
    """Загружает и кэширует модель Vosk."""
    global _vosk_model, _model_failed
    if _vosk_model is not None:
        return _vosk_model

    with _model_lock:
        if _vosk_model is not None:
            return _vosk_model

        try:
            import vosk
        except ImportError as error:
            _model_failed = True
            raise RecognitionError(
                "Для локального распознавания установите vosk (pip install vosk)."
            ) from error

        vosk.SetLogLevel(-1)

        model_path = _find_vosk_model_path()
        try:
            if model_path:
                _vosk_model = vosk.Model(model_path)
            else:
                _vosk_model = vosk.Model(lang="ru")
        except Exception as error:
            _model_failed = True
            raise RecognitionError(
                "Не удалось загрузить модель Vosk. Убедитесь, что модель для русского языка "
                "скачана в папку models/ (например, models/vosk-model-small-ru-0.22)."
            ) from error

        _model_failed = False
        return _vosk_model


def _to_mono(data: bytes, channels: int) -> bytes:
    if channels <= 1:
        return data

    try:
        import audioop

        return audioop.tomono(data, 2, 0.5, 0.5)
    except Exception:
        # 16-bit PCM: шаг channels * 2 байта, берем первые 2 байта (левый канал)
        frame_size = channels * 2
        return b"".join(data[i : i + 2] for i in range(0, len(data), frame_size))


def _recognize_vosk(data: bytes, *, channels: int, sample_rate: int) -> str | None:
    import vosk

    model = get_vosk_model()
    mono_data = _to_mono(data, channels)

    with _recognizer_lock:
        rec = _recognizers.get(sample_rate)
        if rec is None:
            rec = vosk.KaldiRecognizer(model, float(sample_rate))
            _recognizers[sample_rate] = rec
        else:
            reset = getattr(rec, "Reset", None)
            if reset is not None:
                reset()
            else:
                rec = vosk.KaldiRecognizer(model, float(sample_rate))
                _recognizers[sample_rate] = rec

        rec.AcceptWaveform(mono_data)
        result = json.loads(rec.FinalResult())

    text = result.get("text", "").strip()
    return text or None


def recognize(data: bytes, *, channels: int, sample_rate: int) -> str | None:
    return _recognize_vosk(data, channels=channels, sample_rate=sample_rate)
