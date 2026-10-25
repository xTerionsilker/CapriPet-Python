"""Постоянный фоновый шум, следующий за амплитудой глитча.

Зацикленный поток белого шума тихо играет всё время. Его громкость следует
за амплитудой визуального глитча, которая остаётся низкой при стандартном
оверлее. Шум генерируется один раз при запуске и подаётся в ``QAudioSink``
через крошечный зацикленный ``QIODevice``, поэтому аудиопоток только
копирует байты.

Изменения громкости сглаживаются за несколько кадров: глитч сообщает новую
амплитуду при каждой перерисовке (~15 раз в секунду), что иначе давало бы
слышимый «zipper»-шум.

Использование::

    from capri.static_noise import StaticNoise

    noise = StaticNoise(window)
    glitch_manager.amplitude_changed.connect(noise.set_amplitude)
    noise.set_enabled(False)   # выключить, оставив устройство открытым
    noise.toggle()             # снова включить, вернёт True
"""

from __future__ import annotations

import random

from PySide6.QtCore import QIODevice, QObject, QTimer
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

_SAMPLE_RATE = 44_100
_CHANNELS = 1
_BUFFER_SECONDS = 2

# Громкость приёмника линейна; значения намеренно тихие, чтобы шум оставался
# под видео даже на максимуме.
_BASE_LEVEL = 0.045 / 10
_PEAK_LEVEL = 0.45 / 10

_SMOOTH_INTERVAL_MS = 50
_SMOOTH_FACTOR = 0.35


class _NoiseSource(QIODevice):
    """Последовательное устройство только для чтения с зацикленным буфером."""

    def __init__(self, data: bytes, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._data = data
        self._pos = 0

    def isSequential(self) -> bool:  # noqa: N802 (Qt naming)
        return True

    def bytesAvailable(self) -> int:  # noqa: N802 (Qt naming)
        # Всегда отдаём данные: приёмник читает непрерывно, а мы идём по кругу.
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
    """Играет зацикленный белый шум, громкость следует амплитуде 0..1."""

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

    # --- публичное API -----------------------------------------------------
    def set_amplitude(self, amplitude: float) -> None:
        """Задать целевую громкость, где 0 — постоянный фоновый уровень."""
        self._target = max(0.0, min(1.0, float(amplitude)))

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Выключить или включить шум, не освобождая аудиоустройство."""
        self._enabled = bool(enabled)
        if not self._enabled and self._sink is not None:
            # Сразу переходим к тишине; иначе фоновое шипение затухает и
            # приёмник остаётся на ненулевом базовом уровне.
            self._current = 0.0
            self._sink.setVolume(0.0)

    def toggle(self) -> bool:
        """Переключить шум и вернуть новое состояние."""
        self.set_enabled(not self._enabled)
        return self._enabled

    def stop(self) -> None:
        """Остановить воспроизведение и освободить аудиоустройство."""
        self._smooth_timer.stop()
        if self._source is not None:
            self._source.close()
            self._source = None
        if self._sink is not None:
            self._sink.stop()
            self._sink.deleteLater()
            self._sink = None

    # --- внутреннее --------------------------------------------------------
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

        # Случайные байты равномерно распределены как знаковые 16-битные
        # сэмплы — это и есть белый шум, намного дешевле randint() на сэмпл.
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
            # Никогда не оставляем приёмник на фоновом уровне при выключении.
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
