from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSource, QMediaDevices

from .recognizer import RecognitionError, check_available, create_recognizer, to_mono
from .vad import EnergyVAD

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16_000
_CHANNELS = 1
_POLL_MS = 35
_MAX_RECORD_MS = 8_000
_DEFAULT_SILENCE_MS = 750
_FAST_SILENCE_MS = 400
_MIN_SPEECH_MS = 180
_CALIBRATION_MS = 250
_RESTART_DELAY_MS = 60
_ERROR_THROTTLE_MS = 15_000


class VoiceInput(QObject):
    """Потоковый ввод голоса с адаптивным VAD и распознаванием в реальном времени."""

    listening_changed = Signal(bool)
    status_changed = Signal(str)
    partial_recognized = Signal(str)
    recognized = Signal(str)
    failed = Signal(str)
    device_changed = Signal(str)

    _text_ready = Signal(str)
    _round_failed = Signal(str)
    _round_empty = Signal()

    def __init__(
        self, parent: QObject | None = None, *, always_on: bool = False
    ) -> None:
        super().__init__(parent)
        self._source: QAudioSource | None = None
        self._io = None
        self._format: QAudioFormat | None = None
        self._selected_device: QAudioDevice | None = None
        self._enabled = False
        self._capturing = False
        self._busy = False
        self._always_on = always_on
        self._is_armed = False

        self._elapsed_ms = 0
        self._silent_ms = 0
        self._speech_ms = 0
        self._speech_started = False
        self._last_error_at = float("-inf")
        self._status = ""

        self._vad = EnergyVAD(sample_rate=_SAMPLE_RATE)

        # Очередь чанков для потокового фонового распознавания
        self._audio_queue: queue.Queue[bytes | None] = queue.Queue()
        self._stream_thread: threading.Thread | None = None
        self._last_partial_text = ""

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POLL_MS)
        self._poll_timer.timeout.connect(self._poll)

        self._restart_timer = QTimer(self)
        self._restart_timer.setSingleShot(True)
        self._restart_timer.timeout.connect(self._begin_round)

        self._text_ready.connect(self._on_text_ready)
        self._round_failed.connect(self._on_round_failed)
        self._round_empty.connect(self._on_round_empty)

    @property
    def is_listening(self) -> bool:
        return self._enabled

    @property
    def is_busy(self) -> bool:
        return self._busy

    @property
    def current_device(self) -> QAudioDevice:
        """Возвращает текущее активное аудиоустройство."""
        if self._selected_device is not None and not self._selected_device.isNull():
            return self._selected_device
        return QMediaDevices.defaultAudioInput()

    @property
    def selected_device(self) -> QAudioDevice | None:
        return self._selected_device

    def set_armed(self, armed: bool) -> None:
        """Сообщает VAD, что бот активирован вейк-вордом (для сокращения задержки тишины)."""
        self._is_armed = armed

    def set_device(self, device: QAudioDevice | None) -> None:
        """Переключает микрофон."""
        self._selected_device = device
        desc = (
            device.description()
            if device is not None and not device.isNull()
            else "По умолчанию"
        )
        self.device_changed.emit(desc)
        if self._capturing:
            self._poll_timer.stop()
            self._stop_stream_worker()
            self._release_source()
            self._capturing = False
            self._begin_round()

    def toggle(self) -> None:
        if self._always_on:
            if not self._enabled and not self._busy:
                self.start()
            return
        if self._enabled:
            self.stop()
        elif not self._busy:
            self.start()

    def start(self) -> None:
        if self._enabled or self._busy:
            return

        self._enabled = True
        self.listening_changed.emit(True)
        self._set_status("Слушаю…")
        self._begin_round()

    def stop(self) -> None:
        if self._always_on:
            return
        self._restart_timer.stop()
        if self._capturing:
            self._poll_timer.stop()
            self._stop_stream_worker()
            self._release_source()
            self._capturing = False
        if not self._enabled:
            return
        self._enabled = False
        self.listening_changed.emit(False)
        self._set_status("")

    def cancel(self) -> None:
        self._restart_timer.stop()
        self._poll_timer.stop()
        self._stop_stream_worker()
        self._release_source()
        self._capturing = False
        if self._enabled:
            self._enabled = False
            self.listening_changed.emit(False)
        self._set_status("")

    def _set_status(self, text: str) -> None:
        if text == self._status:
            return
        self._status = text
        self.status_changed.emit(text)

    @staticmethod
    def _pick_format(device: QAudioDevice) -> QAudioFormat | None:
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
        if not self._enabled or self._capturing or self._busy:
            return

        try:
            check_available()
        except RecognitionError as error:
            self._abort(str(error))
            return

        device = self.current_device
        if device.isNull():
            self._abort("Микрофон не найден.")
            return

        fmt = self._pick_format(device)
        if fmt is None:
            self._abort("Микрофон не поддерживает нужный формат записи.")
            return

        self._format = fmt
        self._elapsed_ms = 0
        self._silent_ms = 0
        self._speech_ms = 0
        self._speech_started = False
        self._last_partial_text = ""
        self._vad.reset()

        # Запускаем фоновый поток Vosk для потокового приема чанков
        self._start_stream_worker(fmt.sampleRate(), fmt.channelCount())

        self._source = QAudioSource(device, fmt, self)
        self._source.setBufferSize(fmt.bytesForDuration(400_000))
        self._io = self._source.start()
        if self._io is None:
            self._stop_stream_worker()
            self._release_source()
            self._abort("Не удалось открыть микрофон.")
            return

        self._capturing = True
        self._poll_timer.start()

    def _start_stream_worker(self, sample_rate: int, channels: int) -> None:
        self._stop_stream_worker()
        self._audio_queue = queue.Queue()
        self._stream_thread = threading.Thread(
            target=self._stream_worker,
            args=(sample_rate, channels, self._audio_queue),
            name="capri-vosk-stream",
            daemon=True,
        )
        self._stream_thread.start()

    def _stop_stream_worker(self) -> None:
        if self._stream_thread is not None and self._stream_thread.is_alive():
            self._audio_queue.put(None)
            self._stream_thread = None

    def _abort(self, message: str) -> None:
        self._restart_timer.stop()
        if self._capturing:
            self._poll_timer.stop()
            self._stop_stream_worker()
            self._release_source()
            self._capturing = False
        if self._always_on:
            self._set_status("")
            self.failed.emit(message)
            self._restart_timer.start(1000)
            return
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
            chunk_ms = self._chunk_duration_ms(len(chunk))
            self._elapsed_ms += chunk_ms

            is_voice, _rms = self._vad.is_speech(chunk)

            if self._elapsed_ms < _CALIBRATION_MS:
                self._silent_ms = 0
            elif is_voice:
                self._speech_started = True
                self._speech_ms += chunk_ms
                self._silent_ms = 0
            elif self._speech_started:
                self._silent_ms += chunk_ms

            # Направляем аудио напрямую в KaldiRecognizer
            self._audio_queue.put(chunk)

        # Адаптивный порог тишины: 400 мс если ждем команду, иначе 750 мс
        silence_threshold = _FAST_SILENCE_MS if self._is_armed else _DEFAULT_SILENCE_MS

        if self._elapsed_ms >= _MAX_RECORD_MS or (
            self._speech_started and self._silent_ms >= silence_threshold
        ):
            self._finish_round()

    def _chunk_duration_ms(self, byte_count: int) -> int:
        assert self._format is not None
        frames = byte_count / max(1, self._format.bytesPerFrame())
        rate = max(1, self._format.sampleRate())
        return max(1, round(frames / rate * 1000))

    def _release_source(self) -> None:
        if self._source is not None:
            self._source.stop()
            self._source.deleteLater()
            self._source = None
        self._io = None

    def _finish_round(self) -> None:
        if not self._capturing:
            return

        self._poll_timer.stop()
        self._release_source()
        self._capturing = False

        if self._speech_ms < _MIN_SPEECH_MS:
            self._stop_stream_worker()
            self._schedule_next()
            return

        self._busy = True
        self._set_status("Распознаю…")
        # Сигнализируем потоку о завершении фразы
        self._audio_queue.put(None)

    def _stream_worker(
        self, sample_rate: int, channels: int, q: queue.Queue[bytes | None]
    ) -> None:
        try:
            rec = create_recognizer(sample_rate)
        except Exception as error:
            logger.warning("Не удалось инициализировать KaldiRecognizer: %s", error)
            self._round_failed.emit("Ошибка инициализации распознавания.")
            return

        has_speech = False
        while True:
            try:
                chunk = q.get(timeout=0.2)
            except queue.Empty:
                continue

            if chunk is None:
                # Конец фразы — получаем финальный результат
                break

            has_speech = True
            mono = to_mono(chunk, channels)
            if rec.AcceptWaveform(mono):
                res = json.loads(rec.Result())
                text = res.get("text", "").strip()
                if text:
                    self._last_partial_text = text
                    self.partial_recognized.emit(text)
            else:
                partial = json.loads(rec.PartialResult())
                p_text = partial.get("partial", "").strip()
                if p_text and p_text != self._last_partial_text:
                    self._last_partial_text = p_text
                    self.partial_recognized.emit(p_text)

        if not has_speech:
            self._round_empty.emit()
            return

        try:
            final_res = json.loads(rec.FinalResult())
            final_text = final_res.get("text", "").strip()
        except Exception:
            final_text = ""

        final_text = final_text or self._last_partial_text

        if not final_text:
            self._round_empty.emit()
            return

        self._text_ready.emit(final_text)

    def _schedule_next(self) -> None:
        if not self._enabled:
            self._set_status("")
            return
        self._set_status("Слушаю…")
        self._restart_timer.start(_RESTART_DELAY_MS)

    def _on_text_ready(self, text: str) -> None:
        self._busy = False
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
