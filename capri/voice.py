"""Постоянное прослушивание микрофона с распознаванием коротких фраз.

После включения модуль записывает речь отрезками: сам определяет конец
фразы по тишине, распознаёт её в фоновом потоке и сразу начинает новый
отрезок, пока прослушивание не остановят. Для распознавания используется
пакет ``SpeechRecognition`` (Google Web Speech, язык ``ru-RU``), поэтому
нужен доступ в интернет. Если пакет не установлен или микрофон недоступен,
приложение продолжает работать с текстовым вводом.

Модуль сообщает только распознанный текст; ключевые слова («капри»,
«каприкорд») и окно ожидания команды разбирает вызывающая сторона.

Использование::

    from capri.voice import VoiceInput

    voice = VoiceInput(window)
    voice.recognized.connect(window.process_voice_text)
    voice.failed.connect(window.speak)
    voice.toggle()  # включить или выключить постоянное прослушивание
"""

from __future__ import annotations

import io
import math
import threading
import time
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
# Небольшая пауза между отрезками, чтобы микрофон не оставался открытым
# непрерывно и Qt успевал освободить устройство.
_RESTART_DELAY_MS = 120
# Ошибки распознавания не должны повторяться в облачке каждые пару секунд.
_ERROR_THROTTLE_MS = 15_000


class VoiceInput(QObject):
    """Слушает микрофон отрезками и сообщает распознанный текст."""

    listening_changed = Signal(bool)
    status_changed = Signal(str)
    recognized = Signal(str)
    failed = Signal(str)

    # Результат распознавания приходит из фонового потока, поэтому
    # возвращаем его в поток Qt через сигналы.
    _text_ready = Signal(str)
    _round_failed = Signal(str)
    _round_empty = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source: QAudioSource | None = None
        self._io = None
        self._format: QAudioFormat | None = None
        self._buffer = bytearray()
        self._enabled = False
        self._capturing = False
        self._busy = False
        self._elapsed_ms = 0
        self._silent_ms = 0
        self._speech_ms = 0
        self._speech_started = False
        self._last_error_at = float("-inf")
        self._status = ""

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POLL_MS)
        self._poll_timer.timeout.connect(self._poll)

        self._restart_timer = QTimer(self)
        self._restart_timer.setSingleShot(True)
        self._restart_timer.timeout.connect(self._begin_round)

        self._text_ready.connect(self._on_text_ready)
        self._round_failed.connect(self._on_round_failed)
        self._round_empty.connect(self._on_round_empty)

    # --- публичное API -----------------------------------------------------
    @property
    def is_listening(self) -> bool:
        """Включено ли постоянное прослушивание (не отдельный отрезок)."""
        return self._enabled

    @property
    def is_busy(self) -> bool:
        return self._busy

    def toggle(self) -> None:
        """Включить прослушивание или выключить его."""
        if self._enabled:
            self.stop()
        elif not self._busy:
            self.start()

    def start(self) -> None:
        """Начать постоянное прослушивание микрофона по умолчанию."""
        if self._enabled:
            return
        if self._busy:
            return

        self._enabled = True
        self.listening_changed.emit(True)
        self._set_status("Слушаю…")
        self._begin_round()

    def stop(self) -> None:
        """Выключить прослушивание и отбросить незаконченный отрезок."""
        self._restart_timer.stop()
        if self._capturing:
            self._poll_timer.stop()
            self._release_source()
            self._capturing = False
            self._buffer.clear()
        if not self._enabled:
            return
        self._enabled = False
        self.listening_changed.emit(False)
        self._set_status("")

    def cancel(self) -> None:
        """Прервать прослушивание без сообщений (например, при закрытии)."""
        self._restart_timer.stop()
        self._poll_timer.stop()
        self._release_source()
        self._capturing = False
        self._buffer.clear()
        if self._enabled:
            self._enabled = False
            self.listening_changed.emit(False)
        self._set_status("")

    def _set_status(self, text: str) -> None:
        """Сообщить статус, только если он действительно изменился."""
        if text == self._status:
            return
        self._status = text
        self.status_changed.emit(text)

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

    def _begin_round(self) -> None:
        """Открыть микрофон и начать новый отрезок записи."""
        if not self._enabled or self._capturing or self._busy:
            return

        try:
            import speech_recognition  # noqa: F401
        except ImportError:
            self._abort("Для голосового ввода установите SpeechRecognition.")
            return

        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            self._abort("Микрофон не найден.")
            return

        fmt = self._pick_format(device)
        if fmt is None:
            self._abort("Микрофон не поддерживает нужный формат записи.")
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
            self._abort("Не удалось открыть микрофон.")
            return

        self._capturing = True
        self._poll_timer.start()

    def _abort(self, message: str) -> None:
        """Выключить прослушивание из-за неустранимой ошибки."""
        self._restart_timer.stop()
        if self._enabled:
            self._enabled = False
            self.listening_changed.emit(False)
        self._set_status("")
        self.failed.emit(message)

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
            self._finish_round()

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
    def _finish_round(self) -> None:
        """Закрыть текущий отрезок и отправить его на распознавание."""
        if not self._capturing:
            return

        self._poll_timer.stop()
        self._release_source()
        self._capturing = False

        data = bytes(self._buffer)
        self._buffer.clear()
        if self._speech_ms < _MIN_SPEECH_MS or not data:
            # Тишина — просто начинаем следующий отрезок.
            self._schedule_next()
            return

        self._busy = True
        self._set_status("Распознаю…")
        threading.Thread(
            target=self._recognize,
            args=(data, self._format),
            name="capri-voice",
            daemon=True,
        ).start()

    def _schedule_next(self) -> None:
        if not self._enabled:
            self._set_status("")
            return
        self._set_status("Слушаю…")
        self._restart_timer.start(_RESTART_DELAY_MS)

    # --- результат из фонового потока -------------------------------------
    def _on_text_ready(self, text: str) -> None:
        self._busy = False
        # Сначала возвращаемся в режим ожидания, чтобы обработчик текста мог
        # последним обновить статус (например, «жду команду»).
        self._schedule_next()
        if self._enabled:
            self.recognized.emit(text)

    def _on_round_failed(self, message: str) -> None:
        self._busy = False
        now = time.monotonic()
        if self._enabled and (
            now - self._last_error_at >= _ERROR_THROTTLE_MS / 1000
        ):
            self._last_error_at = now
            self.failed.emit(message)
        self._schedule_next()

    def _on_round_empty(self) -> None:
        self._busy = False
        self._schedule_next()

    def _recognize(self, data: bytes, audio_format: QAudioFormat) -> None:
        try:
            import speech_recognition as sr
        except ImportError:
            self._round_failed.emit(
                "Для голосового ввода установите SpeechRecognition."
            )
            return

        try:
            wav = io.BytesIO()
            with wave.open(wav, "wb") as stream:
                stream.setnchannels(audio_format.channelCount())
                stream.setsampwidth(2)
                stream.setframerate(audio_format.sampleRate())
                stream.writeframes(data)
            wav.seek(0)

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="ru-RU").strip()
        except sr.UnknownValueError:
            # Обычное дело при постоянном прослушивании — не мешаем шумом.
            self._round_empty.emit()
            return
        except sr.RequestError:
            self._round_failed.emit(
                "Сервис распознавания недоступен. Проверьте интернет."
            )
            return
        except Exception:
            self._round_failed.emit("Ошибка распознавания речи.")
            return

        if not text:
            self._round_empty.emit()
            return
        self._text_ready.emit(text)
