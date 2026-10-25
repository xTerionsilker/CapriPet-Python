from __future__ import annotations

import random

from PySide6.QtCore import QIODevice, QObject, QTimer
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

_SAMPLE_RATE = 44_100
_CHANNELS = 1
_BUFFER_SECONDS = 2

_BASE_LEVEL = 0.045 / 10
_PEAK_LEVEL = 0.45 / 10

_SMOOTH_INTERVAL_MS = 50
_SMOOTH_FACTOR = 0.35


class _NoiseSource(QIODevice):

    def __init__(self, data: bytes, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._data = data
        self._pos = 0

    def isSequential(self) -> bool:  # noqa: N802 (Qt naming)
        return True

    def bytesAvailable(self) -> int:  # noqa: N802 (Qt naming)
        return len(self._data) + super().bytesAvailable()

    def readData(self, maxlen: int) -> bytes:  # noqa: N802 (Qt naming)
        if maxlen <= 0 or not self._data:
            return b""

        out = bytearray()
        remaining = maxlen
        size = len(self._data)
        while remaining > 0:
            chunk = self._data[self._pos : self._pos + remaining]
            out.extend(chunk)
            self._pos = (self._pos + len(chunk)) % size
            remaining -= len(chunk)
        return bytes(out)

    def writeData(self, _data: bytes) -> int:  # noqa: N802 (Qt naming)
        return 0


class StaticNoise(QObject):

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._sink: QAudioSink | None = None
        self._source: _NoiseSource | None = None
        self._target = 0.0
        self._current = 0.0
        self._enabled = True

        self._smooth_timer = QTimer(self)
        self._smooth_timer.setInterval(_SMOOTH_INTERVAL_MS)
        self._smooth_timer.timeout.connect(self._smooth)

        self._start()

    def set_amplitude(self, amplitude: float) -> None:
        self._target = max(0.0, min(1.0, float(amplitude)))

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if not self._enabled and self._sink is not None:
            self._current = 0.0
            self._sink.setVolume(0.0)

    def toggle(self) -> bool:
        self.set_enabled(not self._enabled)
        return self._enabled

    def stop(self) -> None:
        self._smooth_timer.stop()
        if self._source is not None:
            self._source.close()
            self._source = None
        if self._sink is not None:
            self._sink.stop()
            self._sink.deleteLater()
            self._sink = None

    def _start(self) -> None:
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull():
            return

        fmt = QAudioFormat()
        fmt.setSampleRate(_SAMPLE_RATE)
        fmt.setChannelCount(_CHANNELS)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        if not device.isFormatSupported(fmt):
            fmt = device.preferredFormat()

        samples = _SAMPLE_RATE * _CHANNELS * _BUFFER_SECONDS
        noise = random.randbytes(samples * 2)

        self._source = _NoiseSource(noise, self)
        self._source.open(QIODevice.OpenModeFlag.ReadOnly)
        self._sink = QAudioSink(device, fmt, self)
        self._sink.setVolume(
            self._level_for(self._current) if self._enabled else 0.0
        )
        self._sink.start(self._source)
        self._smooth_timer.start()

    def _smooth(self) -> None:
        if self._sink is None:
            return
        if not self._enabled:
            self._current = 0.0
            self._sink.setVolume(0.0)
            return
        target = self._target
        delta = target - self._current
        if abs(delta) < 0.001:
            self._current = target
        else:
            self._current += delta * _SMOOTH_FACTOR
        self._sink.setVolume(self._level_for(self._current))

    @staticmethod
    def _level_for(amplitude: float) -> float:
        return _BASE_LEVEL + amplitude * (_PEAK_LEVEL - _BASE_LEVEL)
