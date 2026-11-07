"""Модуль захвата звука с микрофона, детекции голоса (VAD) и потокового ввода."""

from __future__ import annotations

import logging
import math
import threading
import time
from array import array
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import (
    QAudioDevice,
    QAudioFormat,
    QAudioSource,
    QMediaDevices,
)

from .recognizer import RecognitionError, check_available, recognize

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16_000
_CHANNELS = 1
_POLL_MS = 50
_MAX_RECORD_MS = 8_000
_SILENCE_MS = 800
_MIN_SPEECH_MS = 250
_RMS_THRESHOLD = 350
_CALIBRATION_MS = 350
_RESTART_DELAY_MS = 120
_ERROR_THROTTLE_MS = 15_000

_FAST_SILENCE_MS = 450
_DEFAULT_SILENCE_MS = 800


class SileroVAD:
    """Детектор голосовой активности (Voice Activity Detection) на базе ONNX-модели Silero VAD."""

    def __init__(
        self, sample_rate: int = 16_000, threshold: float = 0.5
    ) -> None:
        self.sample_rate = sample_rate
        self.threshold = threshold
        self._session: Any = None
        self._state: Any = None
        self._available: bool | None = None
        self._init_session()

    def _find_model_path(self) -> Path | None:
        project_root = Path(__file__).resolve().parents[2]
        candidate = project_root / "models" / "silero_vad.onnx"
        if candidate.exists():
            return candidate
        return None

    def _init_session(self) -> None:
        model_path = self._find_model_path()
        if not model_path:
            self._available = False
            return

        try:
            import numpy as np
            import onnxruntime as ort

            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            opts.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )
            self._session = ort.InferenceSession(
                str(model_path), sess_options=opts
            )
            self._state = np.zeros((2, 1, 128), dtype=np.float32)
            self._available = True
        except Exception as error:
            logger.warning(
                "Не удалось загрузить Silero VAD ONNX: %s", error
            )
            self._available = False

    @property
    def is_available(self) -> bool:
        return bool(self._available and self._session is not None)

    def reset(self) -> None:
        if self.is_available:
            import numpy as np

            self._state = np.zeros((2, 1, 128), dtype=np.float32)

    def is_speech(self, chunk: bytes) -> tuple[bool, float]:
        if not self.is_available:
            return False, 0.0

        try:
            import numpy as np

            audio_data = (
                np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
                / 32768.0
            )
            if len(audio_data) == 0:
                return False, 0.0

            chunk_size = 512
            total_samples = len(audio_data)
            max_prob = 0.0

            sr_tensor = np.array(self.sample_rate, dtype=np.int64)

            for i in range(0, total_samples, chunk_size):
                sub_chunk = audio_data[i : i + chunk_size]
                if len(sub_chunk) < chunk_size:
                    padded = np.zeros(chunk_size, dtype=np.float32)
                    padded[: len(sub_chunk)] = sub_chunk
                    sub_chunk = padded

                input_tensor = np.expand_dims(sub_chunk, axis=0)
                out, self._state = self._session.run(
                    None,
                    {
                        "input": input_tensor,
                        "state": self._state,
                        "sr": sr_tensor,
                    },
                )
                prob = float(out[0][0])
                if prob > max_prob:
                    max_prob = prob

            return max_prob >= self.threshold, max_prob
        except Exception as error:
            logger.debug("Ошибка инференса Silero VAD: %s", error)
            return False, 0.0


class VoiceInput(QObject):
    """Захват аудиопотока с микрофона и координация распознавания речи."""

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
        self._buffer = bytearray()
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
        if (
            self._selected_device is not None
            and not self._selected_device.isNull()
        ):
            return self._selected_device
        return QMediaDevices.defaultAudioInput()

    @property
    def selected_device(self) -> QAudioDevice | None:
        return self._selected_device

    def set_armed(self, armed: bool) -> None:
        self._is_armed = armed

    def set_device(self, device: QAudioDevice | None) -> None:
        self._selected_device = device
        desc = (
            device.description()
            if device is not None and not device.isNull()
            else "По умолчанию"
        )
        self.device_changed.emit(desc)

        if self._capturing:
            self._poll_timer.stop()
            self._release_source()
            self._capturing = False
            self._buffer.clear()
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
        if self._enabled:
            return
        if self._busy:
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
            self._release_source()
            self._capturing = False
            self._buffer.clear()
        if not self._enabled:
            return
        self._enabled = False
        self.listening_changed.emit(False)
        self._set_status("")

    def cancel(self) -> None:
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
        if text == self._status:
            return
        self._status = text
        self.status_changed.emit(text)

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
        self._restart_timer.stop()
        if self._capturing:
            self._poll_timer.stop()
            self._release_source()
            self._capturing = False
            self._buffer.clear()
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
            self._buffer.extend(chunk)
            level = self._rms(chunk)
            chunk_ms = self._chunk_duration_ms(len(chunk))
            self._elapsed_ms += chunk_ms
            if self._elapsed_ms < _CALIBRATION_MS:
                self._silent_ms = 0
            elif level >= _RMS_THRESHOLD:
                self._speech_started = True
                self._speech_ms += chunk_ms
                self._silent_ms = 0
            elif self._speech_started:
                self._silent_ms += chunk_ms

        silence_limit = (
            _FAST_SILENCE_MS if self._is_armed else _DEFAULT_SILENCE_MS
        )
        if self._elapsed_ms >= _MAX_RECORD_MS or (
            self._speech_started and self._silent_ms >= silence_limit
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

    def _finish_round(self) -> None:
        if not self._capturing:
            return

        self._poll_timer.stop()
        self._release_source()
        self._capturing = False

        data = bytes(self._buffer)
        self._buffer.clear()
        if self._speech_ms < _MIN_SPEECH_MS or not data:
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

    def _recognize(self, data: bytes, audio_format: QAudioFormat) -> None:
        try:
            text = recognize(
                data,
                channels=audio_format.channelCount(),
                sample_rate=audio_format.sampleRate(),
            )
        except RecognitionError as error:
            self._round_failed.emit(str(error))
            return
        except Exception:
            self._round_failed.emit("Ошибка распознавания речи.")
            return

        if not text:
            self._round_empty.emit()
            return
        self._text_ready.emit(text)
