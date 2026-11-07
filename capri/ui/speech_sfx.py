"""Синтез и воспроизведение звуковых эффектов речи и интерфейса.

Генерирует процедурные аудиофайлы (свисты, клики печатной машинки, молнии,
системные переходы) и управляет их воспроизведением через QSoundEffect.
"""

from __future__ import annotations

import logging
import math
import random
import struct
import tempfile
import time
import wave
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QMediaDevices, QSoundEffect

logger = logging.getLogger(__name__)


def _generate_swoosh_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.10
) -> None:
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        freq = 350.0 + 1250.0 * (p**1.4)

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


def _generate_close_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.10
) -> None:
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        freq = 1400.0 - 1100.0 * (p**0.8)

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


def _generate_chirp_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.02
) -> None:
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        freq = 1900.0 - 500.0 * p

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


def _generate_teleport_drop_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.45
) -> None:

    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(999)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        bass_freq = 35.0 + 145.0 * math.exp(-6.5 * p)
        sub_bass = math.sin(2.0 * math.pi * bass_freq * t)

        distorted_sub = math.tanh(sub_bass * 2.8) * 0.75

        click = 0.0
        if t < 0.035:
            cp = t / 0.035
            click = rng.uniform(-1.0, 1.0) * (1.0 - cp) ** 2.0 * 0.65

        sparkle = 0.0
        if 0.05 < t < 0.20:
            sp = (t - 0.05) / 0.15
            sparkle = (
                rng.uniform(-1.0, 1.0)
                * math.sin(2.0 * math.pi * 3200.0 * t)
                * (1.0 - sp)
                * 0.25
            )

        env = (1.0 - p) ** 1.4
        val = math.tanh(distorted_sub * 0.8 + click + sparkle) * 0.85 * env
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_lightning_strike_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.42
) -> None:
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(1337)
    for i in range(num_samples):
        t = i / sample_rate

        snap = 0.0
        if t < 0.025:
            snap_env = math.sin(math.pi * (t / 0.025))
            snap_freq = 3400.0 - 2400.0 * (t / 0.025)
            noise = rng.uniform(-1.0, 1.0)
            snap = (
                0.5 * math.sin(2.0 * math.pi * snap_freq * t) + 0.5 * noise
            ) * snap_env

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

        boom = 0.0
        if t > 0.02:
            boom_t = t - 0.02
            boom_dur = duration - 0.02
            boom_p = boom_t / boom_dur
            boom_env = math.sin(math.pi * (boom_p**0.5)) * (
                (1.0 - boom_p) ** 1.8
            )
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


def _generate_lightning_arc_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.20
) -> None:
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


def _generate_lightning_zap_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.08
) -> None:
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(777)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        env = (1.0 - p) ** 2.2
        freq = 2600.0 - 2100.0 * p
        val = (
            0.6 * math.sin(2.0 * math.pi * freq * t)
            + 0.4 * rng.uniform(-1.0, 1.0)
        ) * env
        val = math.tanh(val * 1.5) * 0.70
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_session_lock_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.72
) -> None:
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
            click = (
                0.22 * rng.uniform(-1.0, 1.0) * (1.0 - (t - 0.25) / 0.04)
            )

        val = (
            math.tanh((servo + beep + click) * 1.35)
            * 0.62
            * (1.0 - p * 0.25)
        )
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_session_power_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.95
) -> None:
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
            clatter = (
                0.28 * rng.uniform(-1.0, 1.0) * (1.0 - (t - 0.18) / 0.12)
            )

        thud = 0.0
        if 0.55 <= t < 0.95:
            tp = (t - 0.55) / 0.40
            thud = (
                0.55
                * math.sin(2.0 * math.pi * (48.0 - 16.0 * tp) * t)
                * (1.0 - tp) ** 2.0
            )

        val = math.tanh((tone + clatter + thud) * 1.25) * 0.70
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_session_suspend_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 1.05
) -> None:
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        breath = math.sin(
            2.0
            * math.pi
            * (78.0 + 9.0 * math.sin(2.0 * math.pi * 0.7 * t))
            * t
        )
        pad = (
            (
                0.42 * math.sin(2.0 * math.pi * 146.83 * t)
                + 0.24 * math.sin(2.0 * math.pi * 220.0 * t)
                + 0.18 * math.sin(2.0 * math.pi * 293.66 * t)
            )
            * (0.55 + 0.45 * math.sin(2.0 * math.pi * 1.6 * t))
            * 0.6
        )

        blip = 0.0
        if 0.20 <= t < 0.34:
            bp = (t - 0.20) / 0.14
            blip = (
                0.30
                * math.sin(2.0 * math.pi * (880.0 - 240.0 * bp) * t)
                * math.sin(math.pi * bp)
            )

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


def _generate_session_reboot_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.95
) -> None:
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
            lock_beep = (
                0.30
                * math.sin(2.0 * math.pi * 1568.0 * t)
                * math.sin(math.pi * bp) ** 1.3
            )

        val = (
            math.tanh((arp + static + lock_beep) * 1.35)
            * 0.58
            * (1.0 - p * 0.18)
        )
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_target_acquired_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.18
) -> None:
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        # Cyber lock-on tone: dual pitch beep with metallic ping
        f1 = 880.0 if p < 0.5 else 1760.0
        env = (1.0 - (p % 0.5) / 0.5) ** 1.5
        val = 0.35 * math.sin(2.0 * math.pi * f1 * t) * env
        val += 0.15 * math.sin(2.0 * math.pi * 2600.0 * t) * env
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _generate_data_rip_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 0.35
) -> None:
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(42)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        env = (1.0 - p) ** 1.2
        # Data rip sound: harsh static + descending tone + crunch
        freq = 1200.0 * (1.0 - p) + 60.0
        tone = math.sin(2.0 * math.pi * freq * t)
        noise = rng.uniform(-1.0, 1.0)
        distortion = 1.0 if (noise + tone) > 0.4 else -1.0 if (noise + tone) < -0.4 else (noise + tone)
        val = 0.45 * distortion * env
        sample = int(val * 32767)
        frames.extend(struct.pack("<h", max(-32768, min(32767, sample))))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


class SpeechSFX(QObject):
    """Менеджер процедурных звуковых эффектов речи и интерфейсных событий."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._enabled = True
        self._speech_sound_enabled = True
        self._effects_sound_enabled = True
        self._volume = 0.5
        self._throttle_interval = 0.045
        self._last_chirp_time = 0.0
        self._available = False

        self._swoosh_path: Path | None = None
        self._close_path: Path | None = None
        self._chirp_path: Path | None = None
        self._lightning_strike_path: Path | None = None
        self._lightning_arc_path: Path | None = None
        self._lightning_zap_path: Path | None = None
        self._target_acquired_path: Path | None = None
        self._data_rip_path: Path | None = None
        self._session_paths: dict[str, Path] = {}

        self._swoosh_effect: QSoundEffect | None = None
        self._close_effect: QSoundEffect | None = None
        self._lightning_strike_effect: QSoundEffect | None = None
        self._lightning_arc_effect: QSoundEffect | None = None
        self._lightning_zap_effect: QSoundEffect | None = None
        self._target_acquired_effect: QSoundEffect | None = None
        self._data_rip_effect: QSoundEffect | None = None
        self._session_effects: dict[str, QSoundEffect] = {}
        self._chirp_pool: list[QSoundEffect] = []
        self._chirp_index = 0
        self._suppressed = False

        self._media_devices = QMediaDevices(self)
        self._media_devices.audioOutputsChanged.connect(
            self._on_audio_outputs_changed
        )

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
            drop_path = temp_dir / "cyber_teleport_drop.wav"
            target_path = temp_dir / "cyber_target_acquired.wav"
            data_rip_path = temp_dir / "cyber_data_rip.wav"

            session_specs = {
                "lock": (
                    "cyber_session_lock.wav",
                    _generate_session_lock_wav,
                ),
                "power_off": (
                    "cyber_session_power.wav",
                    _generate_session_power_wav,
                ),
                "suspend": (
                    "cyber_session_suspend.wav",
                    _generate_session_suspend_wav,
                ),
                "reboot": (
                    "cyber_session_reboot.wav",
                    _generate_session_reboot_wav,
                ),
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
            if not drop_path.exists():
                _generate_teleport_drop_wav(drop_path)
            if not target_path.exists():
                _generate_target_acquired_wav(target_path)
            if not data_rip_path.exists():
                _generate_data_rip_wav(data_rip_path)

            self._swoosh_path = swoosh_path
            self._close_path = close_path
            self._chirp_path = chirp_path
            self._lightning_strike_path = strike_path
            self._lightning_arc_path = arc_path
            self._lightning_zap_path = zap_path
            self._teleport_drop_path = drop_path
            self._target_acquired_path = target_path
            self._data_rip_path = data_rip_path

            for action, (filename, generator) in session_specs.items():
                path = temp_dir / filename
                if not path.exists():
                    generator(path)
                self._session_paths[action] = path
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(self._volume * 0.85)
                self._session_effects[action] = effect

            swoosh = QSoundEffect(self)
            swoosh.setSource(QUrl.fromLocalFile(str(swoosh_path)))
            swoosh.setVolume(self._volume)
            self._swoosh_effect = swoosh

            close_sfx = QSoundEffect(self)
            close_sfx.setSource(QUrl.fromLocalFile(str(close_path)))
            close_sfx.setVolume(self._volume)
            self._close_effect = close_sfx

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

            drop_sfx = QSoundEffect(self)
            drop_sfx.setSource(QUrl.fromLocalFile(str(drop_path)))
            drop_sfx.setVolume(self._volume * 0.95)
            self._teleport_drop_effect = drop_sfx

            target_sfx = QSoundEffect(self)
            target_sfx.setSource(QUrl.fromLocalFile(str(target_path)))
            target_sfx.setVolume(self._volume * 0.8)
            self._target_acquired_effect = target_sfx

            rip_sfx = QSoundEffect(self)
            rip_sfx.setSource(QUrl.fromLocalFile(str(data_rip_path)))
            rip_sfx.setVolume(self._volume * 0.9)
            self._data_rip_effect = rip_sfx

            chirp_url = QUrl.fromLocalFile(str(chirp_path))
            self._chirp_pool = []
            for _ in range(3):
                effect = QSoundEffect(self)
                effect.setSource(chirp_url)
                effect.setVolume(self._volume * 0.7)
                self._chirp_pool.append(effect)

            self._available = True
        except Exception as exc:
            logger.warning(
                "Не удалось инициализировать SFX звуки: %s. Работаем в беззвучном режиме.",
                exc,
            )
            self._available = False

    def _on_audio_outputs_changed(self) -> None:
        self.reload_audio_devices()

    def reload_audio_devices(self) -> None:
        try:
            self._init_sounds()
        except Exception as exc:
            logger.debug("SFX device reload failed: %s", exc)

    def _play_file(
        self, path: Path | None, fallback_effect: QSoundEffect | None
    ) -> None:
        if not self.is_enabled() or fallback_effect is None:
            return
        try:
            if (
                fallback_effect.status() == QSoundEffect.Status.Error
                and path is not None
                and path.exists()
            ):
                fallback_effect.setSource(QUrl.fromLocalFile(str(path)))
            fallback_effect.play()
        except Exception as exc:
            logger.debug("QSoundEffect error: %s", exc)

    @property
    def is_available(self) -> bool:
        return self._available

    def is_enabled(self) -> bool:
        return self._enabled and self._available and not self._suppressed

    def set_suppressed(self, suppressed: bool) -> None:
        self._suppressed = bool(suppressed)

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
        if (
            hasattr(self, "_teleport_drop_effect")
            and self._teleport_drop_effect is not None
        ):
            self._teleport_drop_effect.setVolume(self._volume * 0.95)
        if (
            hasattr(self, "_target_acquired_effect")
            and self._target_acquired_effect is not None
        ):
            self._target_acquired_effect.setVolume(self._volume * 0.8)
        if (
            hasattr(self, "_data_rip_effect")
            and self._data_rip_effect is not None
        ):
            self._data_rip_effect.setVolume(self._volume * 0.9)
        for effect in self._session_effects.values():
            effect.setVolume(self._volume * 0.85)
        for effect in self._chirp_pool:
            effect.setVolume(self._volume * 0.7)

    def play_swoosh(self) -> None:
        if not self.is_speech_sound_enabled():
            return
        self._play_file(self._swoosh_path, self._swoosh_effect)

    def play_close(self) -> None:
        if not self.is_speech_sound_enabled():
            return
        self._play_file(self._close_path, self._close_effect)

    def play_lightning_strike(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            self._lightning_strike_path, self._lightning_strike_effect
        )

    def play_lightning_arc(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            self._lightning_arc_path, self._lightning_arc_effect
        )

    def play_lightning_zap(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            self._lightning_zap_path, self._lightning_zap_effect
        )

    def play_teleport_drop(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_teleport_drop_path", None),
            getattr(self, "_teleport_drop_effect", None),
        )

    def play_target_acquired(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_target_acquired_path", None),
            getattr(self, "_target_acquired_effect", None),
        )

    def play_data_rip(self) -> None:
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_data_rip_path", None),
            getattr(self, "_data_rip_effect", None),
        )

    def play_session_action(self, action: str) -> None:
        if not self.is_effects_sound_enabled():
            return
        path = self._session_paths.get(action)
        self._play_file(path, self._session_effects.get(action))

    def play_chirp(self) -> None:
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
            self._chirp_index = (self._chirp_index + 1) % len(
                self._chirp_pool
            )

        self._play_file(self._chirp_path, fallback)

    def stop_all(self, timeout: float = 0.3) -> None:
        pass


class _SpeechSFXHolder:
    instance: SpeechSFX | None = None


def get_speech_sfx() -> SpeechSFX:
    if _SpeechSFXHolder.instance is None:
        _SpeechSFXHolder.instance = SpeechSFX()
    return _SpeechSFXHolder.instance
