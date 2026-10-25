"""Распознавание коротких фраз: WAV-кодирование и Google Web Speech.

Отделено от ``capri.voice``: захват микрофона живёт в Qt-потоке, а здесь —
чистая функция, которую удобно вызывать в фоновом потоке без объектов Qt.
Нужен пакет ``SpeechRecognition`` и доступ в интернет.

Использование::

    from capri.recognizer import RecognitionError, recognize

    try:
        text = recognize(pcm_bytes, channels=1, sample_rate=16_000)
    except RecognitionError as error:
        print(error)   # нет пакета, нет связи, отклонённый запрос
"""

from __future__ import annotations

import io
import wave

#: Язык распознавания Google Web Speech.
LANGUAGE = "ru-RU"


class RecognitionError(RuntimeError):
    """Распознавание недоступно: нет пакета, связи или ответа сервиса."""


def recognize(data: bytes, *, channels: int, sample_rate: int) -> str | None:
    """Распознать 16-битный PCM. ``None`` — речь не распознана.

    ``data`` — сырой поток ``Int16`` длительностью в несколько секунд.
    Неустранимые проблемы оформляются как :class:`RecognitionError`.
    """
    try:
        import speech_recognition as sr
    except ImportError as error:
        raise RecognitionError(
            "Для голосового ввода установите SpeechRecognition."
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
        # Обычное дело при постоянном прослушивании — не мешаем шумом.
        return None
    except sr.RequestError as error:
        raise RecognitionError(
            "Сервис распознавания недоступен. Проверьте интернет."
        ) from error

    return text or None
