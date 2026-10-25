from __future__ import annotations

import io
import wave

LANGUAGE = "ru-RU"


class RecognitionError(RuntimeError):
    pass

def recognize(data: bytes, *, channels: int, sample_rate: int) -> str | None:
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
        return None
    except sr.RequestError as error:
        raise RecognitionError(
            "Сервис распознавания недоступен. Проверьте интернет."
        ) from error

    return text or None
