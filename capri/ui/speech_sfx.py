from __future__ import annotations

import logging
import math
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

logger = logging.getLogger(__name__)


def _find_system_player() -> str | None:
    """Ищет доступную системную утилиту воспроизведения Linux: pw-play -> paplay -> aplay."""
    if sys.platform == "win32":
        return None
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


def _generate_lightning_strike_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.42) -> None:
    """Генерирует мощный киберпанк-удар молнии: плазменный щелчок, высоковольтный треск и саб-басовый гром."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(1337)
    for i in range(num_samples):
        t = i / sample_rate

        # 1. Начальный плазменный щелчок удара (0 - 25 мс)
        snap = 0.0
        if t < 0.025:
            snap_env = math.sin(math.pi * (t / 0.025))
            snap_freq = 3400.0 - 2400.0 * (t / 0.025)
            noise = rng.uniform(-1.0, 1.0)
            snap = (0.5 * math.sin(2.0 * math.pi * snap_freq * t) + 0.5 * noise) * snap_env

        # 2. Высоковольтная дуга / треск разряда (0 - 220 мс)
        arc = 0.0
        if t < 0.22:
            arc_p = t / 0.22
            arc_env = (1.0 - arc_p) ** 1.6
            arc_buzz = (
                0.40 * math.sin(2.0 * math.pi * 110.0 * t)
                + 0.30 * math.sin(2.0 * math.pi * 220.0 * t)
                + 0.20 * math.sin(2.0 * math.pi * 440.0 * t)
                + 0.35 * rng.uniform(-1.0, 1.0)
            )
            spark_spike = 1.9 if rng.random() < 0.04 else 0.0
            arc = (arc_buzz + spark_spike) * arc_env

        # 3. Низкочастотный кибер-раскат грома (20 - 420 мс)
        boom = 0.0
        if t > 0.02:
            boom_t = t - 0.02
            boom_dur = duration - 0.02
            boom_p = boom_t / boom_dur
            boom_env = math.sin(math.pi * (boom_p ** 0.5)) * ((1.0 - boom_p) ** 1.8)
            boom_freq = 65.0 - 35.0 * boom_p
            boom = math.sin(2.0 * math.pi * boom_freq * boom_t) * boom_env

        val = 0.60 * snap + 0.45 * arc + 0.55 * boom
        val = math.tanh(val * 1.25) * 0.75
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_lightning_arc_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.20) -> None:
    """Генерирует треск электрической дуги при пробегании молнии."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(2049)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        env = (1.0 - p) ** 1.3
        f1 = 800.0 + 1400.0 * math.sin(t * 120.0)
        buzz = (
            0.45 * math.sin(2.0 * math.pi * f1 * t)
            + 0.35 * rng.uniform(-1.0, 1.0)
            + (1.6 if rng.random() < 0.06 else 0.0)
        )
        val = math.tanh(buzz * env * 1.1) * 0.65
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_lightning_zap_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.08) -> None:
    """Генерирует быстрый высоковольтный микроразряд (кибер-зэп)."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(777)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        env = (1.0 - p) ** 2.2
        freq = 2600.0 - 2100.0 * p
        val = (0.6 * math.sin(2.0 * math.pi * freq * t) + 0.4 * rng.uniform(-1.0, 1.0)) * env
        val = math.tanh(val * 1.5) * 0.70
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_session_lock_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.72) -> None:
    """Генерирует сервоприводный зажим и два подтверждающих кибер-бипа блокировки."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(2024)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        servo = 0.0
        if t < 0.26:
            sp = t / 0.26
            freq = 170.0 + 460.0 * sp
            servo_env = math.sin(math.pi * sp) ** 1.2
            servo = (
                0.55 * math.sin(2.0 * math.pi * freq * t)
                + 0.25 * math.sin(2.0 * math.pi * freq * 2.0 * t)
                + 0.20 * rng.uniform(-1.0, 1.0)
            ) * servo_env

        beep = 0.0
        for start, freq in ((0.28, 1180.0), (0.42, 1760.0)):
            if start <= t < start + 0.10:
                bp = (t - start) / 0.10
                env = math.sin(math.pi * bp) ** 1.4
                beep += 0.36 * math.sin(2.0 * math.pi * freq * t) * env

        click = 0.0
        if 0.25 <= t < 0.29:
            click = 0.22 * rng.uniform(-1.0, 1.0) * (1.0 - (t - 0.25) / 0.04)

        val = math.tanh((servo + beep + click) * 1.35) * 0.62 * (1.0 - p * 0.25)
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_session_power_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.95) -> None:
    """Генерирует падение энергии ядра: нисходящий свип, треск реле и глухой удар."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(404)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        freq = 72.0 + 820.0 * math.exp(-3.8 * p)
        env = (1.0 - p) ** 0.55
        tone = (
            0.52 * math.sin(2.0 * math.pi * freq * t)
            + 0.22 * math.sin(2.0 * math.pi * freq * 0.5 * t)
            + 0.18 * math.tanh(math.sin(2.0 * math.pi * freq * t) * 3.0)
        ) * env

        clatter = 0.0
        if 0.18 <= t < 0.30:
            clatter = 0.28 * rng.uniform(-1.0, 1.0) * (1.0 - (t - 0.18) / 0.12)

        thud = 0.0
        if 0.55 <= t < 0.95:
            tp = (t - 0.55) / 0.40
            thud = 0.55 * math.sin(2.0 * math.pi * (48.0 - 16.0 * tp) * t) * (1.0 - tp) ** 2.0

        val = math.tanh((tone + clatter + thud) * 1.25) * 0.70
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_session_suspend_wav(file_path: Path, sample_rate: int = 44100, duration: float = 1.05) -> None:
    """Генерирует крио-погружение: низкий пульс, дыхание стазиса и одиночный сонный бип."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        breath = math.sin(2.0 * math.pi * (78.0 + 9.0 * math.sin(2.0 * math.pi * 0.7 * t)) * t)
        pad = (
            0.42 * math.sin(2.0 * math.pi * 146.83 * t)
            + 0.24 * math.sin(2.0 * math.pi * 220.0 * t)
            + 0.18 * math.sin(2.0 * math.pi * 293.66 * t)
        ) * (0.55 + 0.45 * math.sin(2.0 * math.pi * 1.6 * t)) * 0.6

        blip = 0.0
        if 0.20 <= t < 0.34:
            bp = (t - 0.20) / 0.14
            blip = 0.30 * math.sin(2.0 * math.pi * (880.0 - 240.0 * bp) * t) * math.sin(math.pi * bp)

        fade = min(1.0, t / 0.08) * (1.0 - p) ** 1.1
        val = math.tanh((breath * 0.40 + pad + blip) * 1.2) * 0.60 * fade
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_session_reboot_wav(file_path: Path, sample_rate: int = 44100, duration: float = 0.95) -> None:
    """Генерирует загрузочную кибер-последовательность: восходящее арпеджио и бинарный стрекот."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(777)
    notes = (261.63, 329.63, 392.0, 523.25, 659.25, 783.99)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        note_index = min(len(notes) - 1, int(p * len(notes) * 1.2))
        freq = notes[note_index]
        gate = 0.55 + 0.45 * math.sin(2.0 * math.pi * 7.0 * t)
        arp = (
            0.36 * math.sin(2.0 * math.pi * freq * t)
            + 0.18 * math.sin(2.0 * math.pi * freq * 2.0 * t)
        ) * gate

        static = 0.0
        if p < 0.35:
            static = 0.11 * rng.uniform(-1.0, 1.0) * (1.0 - p / 0.35)

        lock_beep = 0.0
        if 0.72 <= t < 0.88:
            bp = (t - 0.72) / 0.16
            lock_beep = 0.30 * math.sin(2.0 * math.pi * 1568.0 * t) * math.sin(math.pi * bp) ** 1.3

        val = math.tanh((arp + static + lock_beep) * 1.35) * 0.58 * (1.0 - p * 0.18)
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
        self._speech_sound_enabled = True
        self._effects_sound_enabled = True
        self._volume = 0.5
        self._throttle_interval = 0.045  # 45 мс минимальный интервал между бипами
        self._last_chirp_time = 0.0
        self._available = False

        self._player_bin = _find_system_player()
        self._processes: list[subprocess.Popen] = []

        self._swoosh_path: Path | None = None
        self._close_path: Path | None = None
        self._chirp_path: Path | None = None
        self._lightning_strike_path: Path | None = None
        self._lightning_arc_path: Path | None = None
        self._lightning_zap_path: Path | None = None
        self._session_paths: dict[str, Path] = {}

        self._swoosh_effect: QSoundEffect | None = None
        self._close_effect: QSoundEffect | None = None
        self._lightning_strike_effect: QSoundEffect | None = None
        self._lightning_arc_effect: QSoundEffect | None = None
        self._lightning_zap_effect: QSoundEffect | None = None
        self._session_effects: dict[str, QSoundEffect] = {}
        self._chirp_pool: list[QSoundEffect] = []
        self._chirp_index = 0

        self._init_sounds()

    def _init_sounds(self) -> None:
        try:
            temp_dir = Path(tempfile.gettempdir()) / "capri_sfx"
            swoosh_path = temp_dir / "cyber_swoosh.wav"
            close_path = temp_dir / "cyber_close.wav"
            chirp_path = temp_dir / "retro_chirp.wav"
            strike_path = temp_dir / "cyber_lightning_strike.wav"
            arc_path = temp_dir / "cyber_lightning_arc.wav"
            zap_path = temp_dir / "cyber_lightning_zap.wav"

            session_specs = {
                "lock": ("cyber_session_lock.wav", _generate_session_lock_wav),
                "power_off": ("cyber_session_power.wav", _generate_session_power_wav),
                "suspend": ("cyber_session_suspend.wav", _generate_session_suspend_wav),
                "reboot": ("cyber_session_reboot.wav", _generate_session_reboot_wav),
            }

            if not swoosh_path.exists():
                _generate_swoosh_wav(swoosh_path)
            if not close_path.exists():
                _generate_close_wav(close_path)
            if not chirp_path.exists():
                _generate_chirp_wav(chirp_path)
            if not strike_path.exists():
                _generate_lightning_strike_wav(strike_path)
            if not arc_path.exists():
                _generate_lightning_arc_wav(arc_path)
            if not zap_path.exists():
                _generate_lightning_zap_wav(zap_path)

            self._swoosh_path = swoosh_path
            self._close_path = close_path
            self._chirp_path = chirp_path
            self._lightning_strike_path = strike_path
            self._lightning_arc_path = arc_path
            self._lightning_zap_path = zap_path

            for action, (filename, generator) in session_specs.items():
                path = temp_dir / filename
                if not path.exists():
                    generator(path)
                self._session_paths[action] = path
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(self._volume * 0.85)
                self._session_effects[action] = effect

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

            # Фолбэки QSoundEffect для молний
            strike_sfx = QSoundEffect(self)
            strike_sfx.setSource(QUrl.fromLocalFile(str(strike_path)))
            strike_sfx.setVolume(self._volume)
            self._lightning_strike_effect = strike_sfx

            arc_sfx = QSoundEffect(self)
            arc_sfx.setSource(QUrl.fromLocalFile(str(arc_path)))
            arc_sfx.setVolume(self._volume * 0.85)
            self._lightning_arc_effect = arc_sfx

            zap_sfx = QSoundEffect(self)
            zap_sfx.setSource(QUrl.fromLocalFile(str(zap_path)))
            zap_sfx.setVolume(self._volume * 0.75)
            self._lightning_zap_effect = zap_sfx

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
            logger.warning("Не удалось инициализировать SFX звуки: %s. Работаем в беззвучном режиме.", exc)
            self._available = False

    def _system_volume_args(self) -> list[str]:
        """Возвращает аргументы громкости для выбранной системной утилиты воспроизведения."""
        if not self._player_bin:
            return []
        player = Path(self._player_bin).name
        if player == "pw-play":
            return ["--volume", f"{self._volume:.3f}"]
        if player == "paplay":
            return [f"--volume={int(round(self._volume * 65536))}"]
        return []

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
                    [self._player_bin, *self._system_volume_args(), str(path)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=(sys.platform != "win32"),
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

    def is_speech_sound_enabled(self) -> bool:
        return self._speech_sound_enabled and self.is_enabled()

    def set_speech_sound_enabled(self, enabled: bool) -> None:
        self._speech_sound_enabled = bool(enabled)

    def is_effects_sound_enabled(self) -> bool:
        return self._effects_sound_enabled and self.is_enabled()

    def set_effects_sound_enabled(self, enabled: bool) -> None:
        self._effects_sound_enabled = bool(enabled)

    def get_volume(self) -> float:
        return self._volume

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._swoosh_effect is not None:
            self._swoosh_effect.setVolume(self._volume)
        if self._close_effect is not None:
            self._close_effect.setVolume(self._volume)
        if self._lightning_strike_effect is not None:
            self._lightning_strike_effect.setVolume(self._volume)
        if self._lightning_arc_effect is not None:
            self._lightning_arc_effect.setVolume(self._volume * 0.85)
        if self._lightning_zap_effect is not None:
            self._lightning_zap_effect.setVolume(self._volume * 0.75)
        for effect in self._session_effects.values():
            effect.setVolume(self._volume * 0.85)
        for effect in self._chirp_pool:
            effect.setVolume(self._volume * 0.7)

    def play_swoosh(self) -> None:
        """Воспроизводит звук открытия облачка (кибер-свуш)."""
        if not self.is_speech_sound_enabled():
            return
        self._play_file(self._swoosh_path, self._swoosh_effect)

    def play_close(self) -> None:
        """Воспроизводит звук закрытия/деактивации облачка."""
        if not self.is_speech_sound_enabled():
            return
        self._play_file(self._close_path, self._close_effect)

    def play_lightning_strike(self) -> None:
        """Воспроизводит мощный удар кибер-молнии."""
        if not self.is_effects_sound_enabled():
            return
        self._play_file(self._lightning_strike_path, self._lightning_strike_effect)

    def play_lightning_arc(self) -> None:
        """Воспроизводит электрический треск бегущей дуги молнии."""
        if not self.is_effects_sound_enabled():
            return
        self._play_file(self._lightning_arc_path, self._lightning_arc_effect)

    def play_lightning_zap(self) -> None:
        """Воспроизводит короткий электрический щелчок микроразряда."""
        if not self.is_effects_sound_enabled():
            return
        self._play_file(self._lightning_zap_path, self._lightning_zap_effect)

    def play_session_action(self, action: str) -> None:
        """Воспроизводит характерный звук сессионной анимации Капри."""
        if not self.is_effects_sound_enabled():
            return
        path = self._session_paths.get(action)
        self._play_file(path, self._session_effects.get(action))

    def play_chirp(self) -> None:
        """
        Воспроизводит ретро-бип при расшифровке глифа.
        Защищен троттлингом (не чаще чем раз в 45 мс).
        """
        if not self.is_speech_sound_enabled() or self._chirp_path is None:
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
