from __future__ import annotations

import logging
import math
from pathlib import Path
import struct
import tempfile
import time
import wave

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

logger = logging.getLogger(__name__)


def _generate_swoosh_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.10) -> None:
    """Генерирует короткий футуристический кибер-свуш (частотный свип ~100 мс)."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        # Частотный свип 350 Гц -> 1600 Гц с легкой нелинейностью
        freq = 350.0 + 1250.0 * (p ** 1.4)
        # Огибающая громкости: атака 10%, затем плавный спад
        if p < 0.1:
            env = p / 0.1
        else:
            env = (1.0 - p) ** 1.3
        val = math.sin(2.0 * math.pi * freq * t) * env * 0.45
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_chirp_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.02) -> None:
    """Генерирует ретро-чирп/бип терминала (~20 мс, 1800-1400 Гц)."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        # Легкий нисходящий ретро-бип 1900 Гц -> 1400 Гц
        freq = 1900.0 - 500.0 * p
        # Огибающая: быстрая атака (2 мс) и экспоненциальный спад
        if p < 0.1:
            env = p / 0.1
        else:
            env = (1.0 - p) ** 1.5
        val = math.sin(2.0 * math.pi * freq * t) * env * 0.22
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


class SpeechSFX(QObject):
    """
    Легковесный аудио-модуль для диалоговых облачков (SFX).
    Обеспечивает воспроизведение кибер-свуша и ретро-бипов терминала
    с внутренним троттлингом и тихим fallback при сбоях аудио.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._enabled = True
        self._volume = 0.5
        self._throttle_interval = 0.045  # 45 мс минимальный интервал между бипами
        self._last_chirp_time = 0.0
        self._available = False

        self._swoosh_effect: QSoundEffect | None = None
        self._chirp_pool: list[QSoundEffect] = []
        self._chirp_index = 0

        self._init_sounds()

    def _init_sounds(self) -> None:
        try:
            temp_dir = Path(tempfile.gettempdir()) / "capri_sfx"
            swoosh_path = temp_dir / "cyber_swoosh.wav"
            chirp_path = temp_dir / "retro_chirp.wav"

            if not swoosh_path.exists():
                _generate_swoosh_wav(swoosh_path)
            if not chirp_path.exists():
                _generate_chirp_wav(chirp_path)

            # Инициализация QSoundEffect для swoosh
            swoosh = QSoundEffect(self)
            swoosh.setSource(QUrl.fromLocalFile(str(swoosh_path)))
            swoosh.setVolume(self._volume)
            self._swoosh_effect = swoosh

            # Пул из 3 эффектов для чирпов (round-robin для устранения наложений)
            chirp_url = QUrl.fromLocalFile(str(chirp_path))
            self._chirp_pool = []
            for _ in range(3):
                effect = QSoundEffect(self)
                effect.setSource(chirp_url)
                effect.setVolume(self._volume * 0.7)
                self._chirp_pool.append(effect)

            self._available = True
        except Exception as exc:
            logger.warning("Не удалось инициализировать SFX звуки речи: %s. Работаем в беззвучном режиме.", exc)
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def is_enabled(self) -> bool:
        return self._enabled and self._available

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def get_volume(self) -> float:
        return self._volume

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._swoosh_effect is not None:
            self._swoosh_effect.setVolume(self._volume)
        for effect in self._chirp_pool:
            effect.setVolume(self._volume * 0.7)

    def play_swoosh(self) -> None:
        """Воспроизводит звук открытия облачка (кибер-свуш)."""
        if not self.is_enabled() or self._swoosh_effect is None:
            return
        try:
            self._swoosh_effect.play()
        except Exception as exc:
            logger.debug("Ошибка при воспроизведении swoosh: %s", exc)

    def play_chirp(self) -> None:
        """
        Воспроизводит ретро-бип при расшифровке глифа.
        Защищен троттлингом (не чаще чем раз в 45 мс).
        """
        if not self.is_enabled() or not self._chirp_pool:
            return
        now = time.monotonic()
        if now - self._last_chirp_time < self._throttle_interval:
            return
        self._last_chirp_time = now

        try:
            effect = self._chirp_pool[self._chirp_index]
            self._chirp_index = (self._chirp_index + 1) % len(self._chirp_pool)
            effect.play()
        except Exception as exc:
            logger.debug("Ошибка при воспроизведении chirp: %s", exc)


_instance: SpeechSFX | None = None


def get_speech_sfx() -> SpeechSFX:
    """Возвращает глобальный синглтон модуля SpeechSFX."""
    global _instance
    if _instance is None:
        _instance = SpeechSFX()
    return _instance
