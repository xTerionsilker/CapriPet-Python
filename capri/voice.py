"""Распознавание голосовых команд через микрофон.

Модуль записывает короткую фразу через QtMultimedia, сам определяет конец
речи по тишине и распознаёт сказанное в фоновом потоке. Для распознавания
используется пакет ``SpeechRecognition`` (Google Web Speech, язык
``ru-RU``), поэтому нужен доступ в интернет. Если пакет не установлен или
микрофон недоступен, приложение продолжает работать с текстовым вводом.

Использование::

    from capri.voice import VoiceInput

    voice = VoiceInput(window)
    voice.recognized.connect(window.process_voice_text)
    voice.failed.connect(window.speak)
    voice.toggle()  # начать или остановить запись
"""

from __future__ import annotations

import io
import math
import struct
import threading
import wave
from array import array

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices

_SAMPLE_RATE = 16_000
_CHANNELS = 1
_POLL_MS = 50
_MAX_RECORD_MS = 8_000
_SILENCE_MS = 1_200
_MIN_SPEECH_MS = 250
_RMS_THRESHOLD = 350
_CALIBRATION_MS = 350


class VoiceInput(QObject):
    """Слушает микрофон и сообщает распознанный текст."""

    listening_changed = Signal(bool)
    status_changed = Signal(str)
    recognized = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source: QAudioSource | None = None
        self._io = None
        self._format: QAudioFormat | None = None
        self._buffer = bytearray()
        self._listening = False
        self._busy = False
        self._elapsed_ms = 0
        self._silent_ms = 0
        self._speech_ms = 0
        self._speech_started = False

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POLL_MS)
        self._poll_timer.timeout.connect(self._poll)

    # --- публичное API -----------------------------------------------------
    @property
    def is_listening(self) -> bool:
        return self._listening

    @property
    def is_busy(self) -> bool:
        return self._busy

    def toggle(self) -> None:
        """Начать запись или остановить её и запустить распознавание."""
        if self._listening:
            self.stop()
        elif not self._busy:
            self.start()

    def start(self) -> None:
        """Начать запись с микрофона по умолчанию."""
        if self._listening or self._busy:
            return

        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            self.failed.emit("Микрофон не найден.")
            return

        fmt = self._pick_format(device)
        if fmt is None:
            self.failed.emit("Микрофон не поддерживает нужный формат записи.")
            return

        self._format = fmt
        self._buffer.clear()
        self._elapsed_ms = 0
        self._silent_ms = 0
        self._speech_ms = 0
        self._speech_started = False

        self._source = QAudioSource(device, fmt, self)
        self._source.setBufferSize(fmt.bytesForDuration(500_000))
        self._io = self._source.start()
        if self._io is None:
            self._release_source()
            self.failed.emit("Не удалось открыть микрофон.")
            return

        self._listening = True
        self._poll_timer.start()
        self.listening_changed.emit(True)
        self.status_changed.emit("Слушаю…")

    def stop(self) -> None:
        """Остановить запись и отправить её на распознавание."""
        if not self._listening:
            return

        self._poll_timer.stop()
        self._release_source()
        self._listening = False
        self.listening_changed.emit(False)

        data = bytes(self._buffer)
        self._buffer.clear()
        if self._speech_ms < _MIN_SPEECH_MS or not data:
            self.status_changed.emit("")
            self.failed.emit("Речь не обнаружена.")
            return

        self._busy = True
        self.status_changed.emit("Распознаю…")
        threading.Thread(
            target=self._recognize,
            args=(data,),
            name="capri-voice",
            daemon=True,
        ).start()

    def cancel(self) -> None:
        """Прервать запись без распознавания (например, при закрытии)."""
        self._poll_timer.stop()
        self._release_source()
        if self._listening:
            self._listening = False
            self.listening_changed.emit(False)
        self.status_changed.emit("")

    # --- запись ------------------------------------------------------------
    @staticmethod
    def _pick_format(device) -> QAudioFormat | None:
        for rate in (_SAMPLE_RATE, 44_100, 48_000):
            fmt = QAudioFormat()
            fmt.setSampleRate(rate)
            fmt.setChannelCount(_CHANNELS)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            if device.isFormatSupported(fmt):
                return fmt

        fmt = device.preferredFormat()
        if fmt.sampleFormat() == QAudioFormat.SampleFormat.Int16:
            return fmt
        return None

    def _poll(self) -> None:
        if self._io is None:
            return

        chunk = bytes(self._io.readAll())
        if chunk:
            self._buffer.extend(chunk)
            level = self._rms(chunk)
            chunk_ms = self._chunk_duration_ms(len(chunk))
            self._elapsed_ms += chunk_ms
            if self._elapsed_ms < _CALIBRATION_MS:
                # Даём микрофону прогреться и не принимаем шум за речь.
                self._silent_ms = 0
            elif level >= _RMS_THRESHOLD:
                self._speech_started = True
                self._speech_ms += chunk_ms
                self._silent_ms = 0
            elif self._speech_started:
                self._silent_ms += chunk_ms

        if self._elapsed_ms >= _MAX_RECORD_MS or (
            self._speech_started and self._silent_ms >= _SILENCE_MS
        ):
            self.stop()

    def _chunk_duration_ms(self, byte_count: int) -> int:
        assert self._format is not None
        frames = byte_count / max(1, self._format.bytesPerFrame())
        rate = max(1, self._format.sampleRate())
        return max(1, round(frames / rate * 1000))

    @staticmethod
    def _rms(chunk: bytes) -> float:
        if len(chunk) < 2:
            return 0.0
        usable = len(chunk) - (len(chunk) % 2)
        samples = array("h")
        samples.frombytes(chunk[:usable])
        if not samples:
            return 0.0
        total = sum(sample * sample for sample in samples)
        return math.sqrt(total / len(samples))

    def _release_source(self) -> None:
        if self._source is not None:
            self._source.stop()
            self._source.deleteLater()
            self._source = None
        self._io = None

    # --- распознавание -----------------------------------------------------
    def _recognize(self, data: bytes) -> None:
        try:
            import speech_recognition as sr
        except ImportError:
            self._finish("Для голосового ввода установите SpeechRecognition.")
            return

        try:
            wav = io.BytesIO()
            with wave.open(wav, "wb") as stream:
                assert self._format is not None
                stream.setnchannels(self._format.channelCount())
                stream.setsampwidth(2)
                stream.setframerate(self._format.sampleRate())
                stream.writeframes(data)
            wav.seek(0)

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="ru-RU").strip()
        except sr.UnknownValueError:
            self._finish("Не удалось разобрать речь.")
            return
        except sr.RequestError:
            self._finish(
                "Сервис распознавания недоступен. Проверьте интернет."
            )
            return
        except Exception:
            self._finish("Ошибка распознавания речи.")
            return

        if not text:
            self._finish("Не удалось разобрать речь.")
            return
        self._busy = False
        self.status_changed.emit("")
        self.recognized.emit(text)

    def _finish(self, message: str) -> None:
        self._busy = False
        self.status_changed.emit("")
        self.failed.emit(message)
