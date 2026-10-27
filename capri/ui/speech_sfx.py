from __future__ import annotations

import logging
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time
import wave

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

logger = logging.getLogger(__name__)


def _find_system_player() -> str | None:
    """Ищет доступную системную утилиту воспроизведения Linux: pw-play -> paplay -> aplay."""
    for cmd in ("pw-play", "paplay", "aplay"):
        path = shutil.which(cmd)
        if path:
            return path
    return None


def _generate_swoosh_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.10) -> None:
    """Генерирует короткий футуристический кибер-свуш (восходящий частотный свип ~100 мс)."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        # Частотный свип 350 Гц -> 1600 Гц с легкой нелинейностью
        freq = 350.0 + 1250.0 * (p ** 1.4)
        # Огибающая громкости: быстрая атака 10%, затем плавный спад
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


def _generate_close_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.10) -> None:
    """Генерирует звук кибер-деактивации / закрытия (нисходящий частотный свип 1400 -> 300 Гц)."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        # Нисходящий свип 1400 Гц -> 300 Гц
        freq = 1400.0 - 1100.0 * (p ** 0.8)
        # Огибающая: быстрая атака 8%, затем экспоненциальное затухание
        if p < 0.08:
            env = p / 0.08
        else:
            env = (1.0 - p) ** 1.5
        val = math.sin(2.0 * math.pi * freq * t) * env * 0.40
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_chirp_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.02) -> None:
    """Генерирует ретро-чирп/бип терминала (~20 мс, 1900-1400 Гц)."""
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
    Обеспечивает надежное неблокирующее воспроизведение через системные утилиты
    Linux (pw-play -> paplay -> aplay) с бесшовным фолбэком на QSoundEffect.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._enabled = True
        self._volume = 0.5
        self._throttle_interval = 0.045  # 45 мс минимальный интервал между бипами
        self._last_chirp_time = 0.0
        self._available = False

        self._player_bin = _find_system_player()
        self._processes: list[subprocess.Popen] = []

        self._swoosh_path: Path | None = None
        self._close_path: Path | None = None
        self._chirp_path: Path | None = None

        self._swoosh_effect: QSoundEffect | None = None
        self._close_effect: QSoundEffect | None = None
        self._chirp_pool: list[QSoundEffect] = []
        self._chirp_index = 0

        self._init_sounds()

    def _init_sounds(self) -> None:
        try:
            temp_dir = Path(tempfile.gettempdir()) / "capri_sfx"
            swoosh_path = temp_dir / "cyber_swoosh.wav"
            close_path = temp_dir / "cyber_close.wav"
            chirp_path = temp_dir / "retro_chirp.wav"

            if not swoosh_path.exists():
                _generate_swoosh_wav(swoosh_path)
            if not close_path.exists():
                _generate_close_wav(close_path)
            if not chirp_path.exists():
                _generate_chirp_wav(chirp_path)

            self._swoosh_path = swoosh_path
            self._close_path = close_path
            self._chirp_path = chirp_path

            # Фолбэк QSoundEffect для swoosh
            swoosh = QSoundEffect(self)
            swoosh.setSource(QUrl.fromLocalFile(str(swoosh_path)))
            swoosh.setVolume(self._volume)
            self._swoosh_effect = swoosh

            # Фолбэк QSoundEffect для close
            close_sfx = QSoundEffect(self)
            close_sfx.setSource(QUrl.fromLocalFile(str(close_path)))
            close_sfx.setVolume(self._volume)
            self._close_effect = close_sfx

            # Пул эффектов для чирпов
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

    def _play_file(self, path: Path | None, fallback_effect: QSoundEffect | None) -> None:
        """Воспроизводит WAV файл через системную утилиту или QSoundEffect фолбэк."""
        if not self.is_enabled() or path is None:
            return

        # Очистка завершившихся процессов
        self._processes = [p for p in self._processes if p.poll() is None]

        played_by_system = False
        if self._player_bin:
            try:
                proc = subprocess.Popen(
                    [self._player_bin, str(path)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                )
                self._processes.append(proc)
                played_by_system = True
            except Exception as exc:
                logger.debug("Системный плеер %s завершился с ошибкой: %s", self._player_bin, exc)

        if not played_by_system and fallback_effect is not None:
            try:
                fallback_effect.play()
            except Exception as exc:
                logger.debug("Фолбэк QSoundEffect ошибка: %s", exc)

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
        if self._close_effect is not None:
            self._close_effect.setVolume(self._volume)
        for effect in self._chirp_pool:
            effect.setVolume(self._volume * 0.7)

    def play_swoosh(self) -> None:
        """Воспроизводит звук открытия облачка (кибер-свуш)."""
        self._play_file(self._swoosh_path, self._swoosh_effect)

    def play_close(self) -> None:
        """Воспроизводит звук закрытия/деактивации облачка."""
        self._play_file(self._close_path, self._close_effect)

    def play_chirp(self) -> None:
        """
        Воспроизводит ретро-бип при расшифровке глифа.
        Защищен троттлингом (не чаще чем раз в 45 мс).
        """
        if not self.is_enabled() or self._chirp_path is None:
            return
        now = time.monotonic()
        if now - self._last_chirp_time < self._throttle_interval:
            return
        self._last_chirp_time = now

        fallback = (
            self._chirp_pool[self._chirp_index]
            if self._chirp_pool
            else None
        )
        if self._chirp_pool:
            self._chirp_index = (self._chirp_index + 1) % len(self._chirp_pool)

        self._play_file(self._chirp_path, fallback)

    def stop_all(self, timeout: float = 0.3) -> None:
        """Ожидает завершения или останавливает запущенные процессы воспроизведения."""
        for p in self._processes:
            try:
                p.wait(timeout=timeout)
            except Exception:
                try:
                    p.kill()
                    p.wait(timeout=0.1)
                except Exception:
                    pass
        self._processes.clear()


_instance: SpeechSFX | None = None


def get_speech_sfx() -> SpeechSFX:
    """Возвращает глобальный синглтон модуля SpeechSFX."""
    global _instance
    if _instance is None:
        _instance = SpeechSFX()
    return _instance
