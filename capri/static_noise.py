"""Constant background static that follows the glitch amplitude.

A looping white-noise stream plays quietly all the time and gets louder as the
visual glitch intensifies. The noise is generated once at startup and fed to a
``QAudioSink`` through a tiny looping ``QIODevice``, so the audio thread only
copies bytes.

Volume changes are smoothed over a few frames: the glitch reports a new
amplitude every repaint (up to ~30 times per second), which would otherwise
produce audible zipper noise.

Usage::

    from capri.static_noise import StaticNoise

    noise = StaticNoise(window)
    glitch_manager.amplitude_changed.connect(noise.set_amplitude)
    noise.set_enabled(False)   # mute while keeping the device open
    noise.toggle()             # back on, returns True
"""

from __future__ import annotations

import random

from PySide6.QtCore import QIODevice, QObject, QTimer
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

_SAMPLE_RATE = 44_100
_CHANNELS = 1
_BUFFER_SECONDS = 2

# The sink volume is linear; these are deliberately on the quiet side so the
# static sits under the video even at its loudest.
_BASE_LEVEL = 0.045 / 10
_PEAK_LEVEL = 0.45 / 10

_SMOOTH_INTERVAL_MS = 50
_SMOOTH_FACTOR = 0.35


class _NoiseSource(QIODevice):
    """A sequential read-only device that loops over a pre-filled buffer."""

    def __init__(self, data: bytes, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._data = data
        self._pos = 0

    def isSequential(self) -> bool:  # noqa: N802 (Qt naming)
        return True

    def bytesAvailable(self) -> int:  # noqa: N802 (Qt naming)
        # Always claim data: the sink reads continuously and we wrap around.
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
    """Plays looping white noise whose volume tracks a 0..1 amplitude."""

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

    # --- public API --------------------------------------------------------
    def set_amplitude(self, amplitude: float) -> None:
        """Set the target loudness, where 0 is the constant idle level."""
        self._target = max(0.0, min(1.0, float(amplitude)))

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Mute or unmute the static without releasing the audio device."""
        self._enabled = bool(enabled)
        if not self._enabled and self._sink is not None:
            # Jump straight to silence; otherwise the idle hiss fades out and
            # the sink is left at its non-zero base level.
            self._current = 0.0
            self._sink.setVolume(0.0)

    def toggle(self) -> bool:
        """Flip the noise on or off and return the new state."""
        self.set_enabled(not self._enabled)
        return self._enabled

    def stop(self) -> None:
        """Stop playback and release the audio device."""
        self._smooth_timer.stop()
        if self._source is not None:
            self._source.close()
            self._source = None
        if self._sink is not None:
            self._sink.stop()
            self._sink.deleteLater()
            self._sink = None

    # --- internals ---------------------------------------------------------
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

        # Random bytes are uniformly distributed signed 16-bit samples, which
        # is exactly white noise and much cheaper than per-sample randint().
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
            # Never leave the sink at the idle base level while muted.
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
