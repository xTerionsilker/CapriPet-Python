from __future__ import annotations

import io
import json
import os
import threading
import wave
from pathlib import Path

LANGUAGE = "ru-RU"

_vosk_model = None
_model_lock = threading.Lock()


class RecognitionError(RuntimeError):
    pass


def get_backend() -> str:
    """Возвращает текущий бэкенд распознавания: 'vosk' (по умолчанию) или 'google'."""
    return os.environ.get("CAPRI_VOICE_BACKEND", "vosk").strip().casefold()


def check_available() -> None:
    """Проверяет доступность необходимых зависимостей для распознавания речи."""
    backend = get_backend()
    if backend == "google":
        try:
            import speech_recognition  # noqa: F401
        except ImportError as error:
            raise RecognitionError(
                "Для распознавания через Google установите SpeechRecognition."
            ) from error
    else:
        try:
            import vosk  # noqa: F401
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


def get_vosk_model():
    """Загружает и кэширует модель Vosk."""
    global _vosk_model
    if _vosk_model is not None:
        return _vosk_model

    with _model_lock:
        if _vosk_model is not None:
            return _vosk_model

        try:
            import vosk
        except ImportError as error:
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
            raise RecognitionError(
                "Не удалось загрузить модель Vosk. Убедитесь, что модель для русского языка "
                "скачана в папку models/ (например, models/vosk-model-small-ru-0.22)."
            ) from error

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

    rec = vosk.KaldiRecognizer(model, float(sample_rate))
    rec.AcceptWaveform(mono_data)
    result = json.loads(rec.FinalResult())
    text = result.get("text", "").strip()
    return text or None


def _recognize_google(data: bytes, *, channels: int, sample_rate: int) -> str | None:
    try:
        import speech_recognition as sr
    except ImportError as error:
        raise RecognitionError(
            "Для распознавания через Google установите SpeechRecognition."
        ) from error

    try:
        wav = io.BytesIO()
        with wave.open(wav, "wb") as stream:
            stream.setnchannels(channels)
            stream.setsampwidth(2)
            stream.setframerate(sample_rate)
            stream.writeframes(data)
        wav.seek(0)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language=LANGUAGE).strip()
    except sr.UnknownValueError:
        return None
    except sr.RequestError as error:
        raise RecognitionError(
            "Сервис распознавания недоступен. Проверьте интернет."
        ) from error

    return text or None


def recognize(data: bytes, *, channels: int, sample_rate: int) -> str | None:
    backend = get_backend()
    if backend == "google":
        return _recognize_google(data, channels=channels, sample_rate=sample_rate)
    return _recognize_vosk(data, channels=channels, sample_rate=sample_rate)
