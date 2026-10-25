"""Распознавание коротких фраз: WAV-кодирование и голосовой движок Windows.

Отделено от ``capri.voice``: захват микрофона живёт в Qt-потоке, а здесь —
чистая функция, которую удобно вызывать в фоновом потоке без объектов Qt.

В Linux Capri отправляла WAV на Google Web Speech. В Windows 11 распознавание
речи встроено в систему: классический движок SAPI (Speech API) работает
**офлайн**, не требует интернета и берёт язык из установленных речевых
пакетов. Модуль обращается к нему через COM-библиотеку ``comtypes``
(ставится из ``requirements.txt``):

* грамматика — свободная диктовка (``ISpDictation``), язык соответствует
  установленному пакету; для русского добавьте «Распознавание речи» с
  русским языком: *Параметры → Время и язык → Произношение*;
* если движок недоступен (речевой пакет не установлен или политика
  блокирует COM), модуль честно бросает :class:`RecognitionError` —
  текстовый ввод при этом продолжает работать.

COM-объекты SAPI однопоточны (STA), поэтому каждый вызов выполняется в
свежем потоке с ``CoInitialize``/``CoUninitialize`` — фоновые потоки
``capri.voice`` переиспользовать их не могут.

Использование::

    from capri.recognizer import RecognitionError, recognize

    try:
        text = recognize(pcm_bytes, channels=1, sample_rate=16_000)
    except RecognitionError as error:
        print(error)   # нет движка, зависание, речь не распознана
"""

from __future__ import annotations

import io
import threading
import wave

#: Сколько секунд ждать окончания распознавания одного отрезка.
RECOGNIZE_TIMEOUT_S = 30.0

#: Строка ошибки, когда голосовой движок Windows недоступен.
NO_ENGINE_MESSAGE = (
    "Голосовое распознавание Windows недоступно. Установите речевой пакет: "
    "Параметры → Время и язык → Произношение."
)

# Констаны SAPI (SPSTREAM_STATUS / SPRECOSTATE / SGDSACTIVE).
_SP_STREAM_END_OF_STREAM = 3
_SP_RECO_SYNC_FETCH = 1
_GRAMMAR_DICTATION_ACTIVE = 1


class RecognitionError(RuntimeError):
    """Распознавание недоступно: нет движка или он не смог ответить."""


def _to_wav_bytes(data: bytes, *, channels: int, sample_rate: int) -> bytes:
    """Обернуть сырой 16-битный PCM в контейнер WAV."""
    wav = io.BytesIO()
    with wave.open(wav, "wb") as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(data)
    return wav.getvalue()


def recognize(data: bytes, *, channels: int, sample_rate: int) -> str | None:
    """Распознать 16-битный PCM голосовым движком Windows.

    ``None`` — речь не распознана (обычное дело при постоянном
    прослушивании). ``data`` — сырой поток ``Int16`` длительностью в
    несколько секунд. Неустранимые проблемы оформляются как
    :class:`RecognitionError`.
    """
    if not data:
        return None

    wav_bytes = _to_wav_bytes(data, channels=channels, sample_rate=sample_rate)

    try:
        import comtypes
        from comtypes.client import CreateObject
    except ImportError as error:
        raise RecognitionError(NO_ENGINE_MESSAGE) from error

    result: dict[str, object] = {}

    def worker() -> None:
        comtypes.CoInitialize()
        try:
            result["text"] = _recognize_with_sapi(CreateObject, wav_bytes)
        except BaseException as error:  # COM бросает разные обёртки
            result["error"] = error
        finally:
            comtypes.CoUninitialize()

    thread = threading.Thread(target=worker, name="capri-sapi", daemon=True)
    thread.start()
    thread.join(RECOGNIZE_TIMEOUT_S)

    if thread.is_alive():
        raise RecognitionError("Голосовой движок Windows не ответил вовремя.")

    error = result.get("error")
    if isinstance(error, RecognitionError):
        raise error
    if error is not None:
        raise RecognitionError(NO_ENGINE_MESSAGE) from error  # type: ignore[misc]

    text = result.get("text")
    return str(text).strip() or None if text else None


def _recognize_with_sapi(create_object, wav_bytes: bytes) -> str | None:
    """Один проход SAPI: подать WAV в распознаватель и забрать текст.

    ``SpInMemoryRecognizer`` — штатный офлайн-движок Windows; вместе с
    грамматикой диктовки он понимает свободную русскую и английскую речь
    без доступа в сеть.
    """
    recognizer = create_object("SAPI.SpInMemoryRecognizer")

    grammar = recognizer.CreateGrammar(0)
    grammar.DictationSet(0).DictationLoad("", _GRAMMAR_DICTATION_ACTIVE)

    stream = create_object("SAPI.SpMemStream")
    stream.Write(wav_bytes, len(wav_bytes))
    stream.Seek(0, 0)
    recognizer.SetInput(stream)

    # Ждём конца потока, затем синхронно забираем лучший результат.
    if not recognizer.WaitForEvent(_SP_STREAM_END_OF_STREAM, 15_000):
        return None
    recognizer.Recognize(None, _SP_RECO_SYNC_FETCH)

    reco = recognizer.RecoResult
    if reco is None:
        return None
    phrase = reco.PhraseInfo
    if phrase is None:
        return None
    return str(phrase.GetText(0, -1, True)).strip() or None
