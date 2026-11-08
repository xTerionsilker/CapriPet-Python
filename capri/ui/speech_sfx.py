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

# Master audio parameters (Studio Trigger cyber soundscape)
DEFAULT_SAMPLE_RATE: int = 44100
SFX_VERSION: str = "v2_trigger"  # Bust cache on generator update


def _write_wav_16bit(file_path: Path, frames: bytearray, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
    """Записывает 16-bit моно PCM WAV файл с атомарным созданием директории."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def _pack_sample(val: float, drive: float = 1.0, master_gain: float = 0.95) -> bytes:
    """Применяет нелинейную сатурацию tanh и упаковывает в 16-bit int."""
    saturated = math.tanh(val * drive) * master_gain
    clamped = max(-1.0, min(1.0, saturated))
    sample = int(clamped * 32767.0)
    return struct.pack("<h", max(-32768, min(32767, sample)))


def _generate_swoosh_wav(
    file_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE, duration: float = 0.12
) -> None:
    """Кинетический CRT-щелчок и развертывание голограммы с высокочастотным свистом."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(101)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        # Экспоненциальный подъем несущей частоты (coil whine разгона)
        freq = 420.0 + 3800.0 * (p**1.8)
        whine = math.sin(2.0 * math.pi * freq * t)

        # Стартовый стеклянный/CRT щелчок лучом
        click = 0.0
        if p < 0.15:
            cp = p / 0.15
            click = math.sin(2.0 * math.pi * 5400.0 * t) * (1.0 - cp) ** 2.0 * 0.7
            if rng.random() < 0.2:
                click += rng.uniform(-0.4, 0.4) * (1.0 - cp)

        env = (math.sin(math.pi * p) ** 0.8) if p < 0.3 else ((1.0 - p) ** 1.4)
        val = (whine * 0.45 + click * 0.55) * env
        frames.extend(_pack_sample(val, drive=1.35, master_gain=0.88))

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_close_wav(
    file_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE, duration: float = 0.09
) -> None:
    """Схлопывание голографического луча: мгновенный срез частоты со статическим щелчком."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(202)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        # Резкое падение частоты вниз («коллапс луча»)
        freq = 3200.0 * math.exp(-12.0 * p) + 120.0
        sweep = math.sin(2.0 * math.pi * freq * t)

        # Завершающий микро-разряд
        zap = 0.0
        if 0.02 <= t < 0.05:
            zap = rng.uniform(-0.6, 0.6) * (1.0 - (t - 0.02) / 0.03)

        env = (1.0 - p) ** 2.2
        val = (sweep * 0.65 + zap * 0.35) * env
        frames.extend(_pack_sample(val, drive=1.4, master_gain=0.85))

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_chirp_wav(
    file_path: Path,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    duration: float = 0.022,
    base_freq: float = 2400.0,
    jitter: float = 0.15,
    style: str = "normal",
) -> None:
    """Высокочастотный кибер-импульс печати с глитч-джиттером и эмоциональной модуляцией."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(int(base_freq * 13 + duration * 1000))
    
    # Расчет эмоциональных модификаторов стиля
    freq_sweep = 0.0
    overdrive = 1.6
    gain = 0.75
    
    if style == "exclamation":  # ! — резкий овердрайв и статический щелчок
        duration = 0.035
        num_samples = int(sample_rate * duration)
        base_freq = 3200.0
        overdrive = 3.2
        gain = 0.95
    elif style == "question":  # ? — восходящий высокочастотный пинг/свист
        duration = 0.032
        num_samples = int(sample_rate * duration)
        base_freq = 1900.0
        freq_sweep = 2200.0
        overdrive = 1.3
        gain = 0.80
    elif style == "ellipsis":  # ... — затухающий шум наводки/шина данных
        duration = 0.038
        num_samples = int(sample_rate * duration)
        base_freq = 1100.0
        overdrive = 1.1
        gain = 0.60

    freq_offset = (rng.random() - 0.5) * 2.0 * jitter * base_freq
    eff_freq = base_freq + freq_offset

    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        # Частотная модуляция
        instant_freq = eff_freq + freq_sweep * p
        carrier = math.sin(2.0 * math.pi * instant_freq * t)

        # Статический шум/глитч импульс
        noise = rng.uniform(-0.35, 0.35) if (style == "ellipsis" or rng.random() < 0.25) else 0.0

        # Острая экспоненциальная огибающая
        if p < 0.12:
            env = p / 0.12
        else:
            env = (1.0 - p) ** 2.2

        val = (carrier * 0.75 + noise * 0.25) * env
        frames.extend(_pack_sample(val, drive=overdrive, master_gain=gain))

    _write_wav_16bit(file_path, frames, sample_rate)


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
    file_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE, duration: float = 0.16
) -> None:
    """Пронзительный кибер-пинг прицела Kiroshi: двухтоновый импульс с резонансом."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        # Двойной щелчок: 1-я половина 1850 Гц, 2-я половина 3700 Гц (октет вверх)
        part_p = (p % 0.5) / 0.5
        f1 = 1850.0 if p < 0.5 else 3700.0
        env = (1.0 - part_p) ** 2.5

        # Высокочастотный металлический призвук
        ping = math.sin(2.0 * math.pi * f1 * t) * 0.65
        harm = math.sin(2.0 * math.pi * (f1 * 2.2) * t) * 0.35
        val = (ping + harm) * env
        frames.extend(_pack_sample(val, drive=1.5, master_gain=0.85))

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_data_rip_wav(
    file_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE, duration: float = 0.32
) -> None:
    """Жесткий цифровой хруст аннигиляции байтов Черного заслона с сатурацией."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(42)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        env = (1.0 - p) ** 1.3

        # Нелинейно падающая несущая частота шины данных
        freq = 2400.0 * math.exp(-8.0 * p) + 80.0
        tone = math.sin(2.0 * math.pi * freq * t)

        # Дискретный шум и цифровой битовый хруст
        noise = rng.uniform(-1.0, 1.0)
        bit_quantized = math.floor((tone + noise * 1.2) * 4.0) / 4.0

        val = (bit_quantized * 0.7 + tone * 0.3) * env
        frames.extend(_pack_sample(val, drive=2.6, master_gain=0.92))

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_voice_start_wav(
    file_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE, duration: float = 0.08
) -> None:
    """Открытие канала нейролинка: двойной быстрый высокочастотный чирп-импульс."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        # Двойной щелчок (2.8 кГц и 3.6 кГц)
        freq = 2800.0 if p < 0.45 else 3600.0
        part_p = (p / 0.45) if p < 0.45 else ((p - 0.45) / 0.55)
        env = (1.0 - part_p) ** 2.0
        val = math.sin(2.0 * math.pi * freq * t) * env
        frames.extend(_pack_sample(val, drive=1.4, master_gain=0.82))

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_voice_success_wav(
    file_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE, duration: float = 0.14
) -> None:
    """Подтверждение распознанной голосовой команды: восходящий кибер-аккорд."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    # Трезвучие пентатоники киберпанка
    tones = (1318.51, 1760.0, 2637.02)  # E6, A6, E7
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        tone_idx = min(len(tones) - 1, int(p * len(tones) * 1.05))
        freq = tones[tone_idx]
        env = (1.0 - p) ** 1.3
        sine = math.sin(2.0 * math.pi * freq * t)
        val = (sine + 0.25 * math.sin(2.0 * math.pi * freq * 2.0 * t)) * env
        frames.extend(_pack_sample(val, drive=1.3, master_gain=0.85))

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_voice_cancel_wav(
    file_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE, duration: float = 0.11
) -> None:
    """Сброс/таймаут голосового ввода: нисходящий деактивационный срез."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        freq = 2200.0 * math.exp(-7.5 * p) + 160.0
        env = (1.0 - p) ** 1.8
        val = math.sin(2.0 * math.pi * freq * t) * env
        frames.extend(_pack_sample(val, drive=1.5, master_gain=0.80))

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_core_destabilize_wav(
    file_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE, duration: float = 0.40
) -> None:
    """Нарастающий писк катушек и дестабилизация ядра биочипа при скуке/перегрузке."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(99)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration
        # Вой катушек нарастает от 2 кГц до 7.5 кГц
        carrier_freq = 2100.0 + 5400.0 * (p**2.2)
        coil = math.sin(2.0 * math.pi * carrier_freq * t)
        # Интермодуляционный биения и электрические спарки
        fm = math.sin(2.0 * math.pi * 32.0 * t)
        spark = rng.uniform(-0.4, 0.4) if rng.random() < 0.15 else 0.0
        env = math.sin(math.pi * p) ** 0.8
        val = (coil * (0.8 + 0.2 * fm) + spark) * env
        frames.extend(_pack_sample(val, drive=2.0, master_gain=0.78))

    _write_wav_16bit(file_path, frames, sample_rate)


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
        self._voice_start_path: Path | None = None
        self._voice_success_path: Path | None = None
        self._voice_cancel_path: Path | None = None
        self._core_destabilize_path: Path | None = None
        self._session_paths: dict[str, Path] = {}

        self._swoosh_effect: QSoundEffect | None = None
        self._close_effect: QSoundEffect | None = None
        self._lightning_strike_effect: QSoundEffect | None = None
        self._lightning_arc_effect: QSoundEffect | None = None
        self._lightning_zap_effect: QSoundEffect | None = None
        self._target_acquired_effect: QSoundEffect | None = None
        self._data_rip_effect: QSoundEffect | None = None
        self._voice_start_effect: QSoundEffect | None = None
        self._voice_success_effect: QSoundEffect | None = None
        self._voice_cancel_effect: QSoundEffect | None = None
        self._core_destabilize_effect: QSoundEffect | None = None
        self._session_effects: dict[str, QSoundEffect] = {}
        self._chirp_pool: list[QSoundEffect] = []
        self._chirp_index = 0
        self._chirp_pools_by_style: dict[str, list[QSoundEffect]] = {}
        self._chirp_indices_by_style: dict[str, int] = {}
        self._chirp_paths_by_style: dict[str, Path] = {}
        self._suppressed = False

        self._media_devices = QMediaDevices(self)
        self._media_devices.audioOutputsChanged.connect(
            self._on_audio_outputs_changed
        )

        self._init_sounds()

    def _init_sounds(self) -> None:
        try:
            temp_dir = Path(tempfile.gettempdir()) / f"capri_sfx_{SFX_VERSION}"
            swoosh_path = temp_dir / "cyber_swoosh.wav"
            close_path = temp_dir / "cyber_close.wav"
            chirp_path = temp_dir / "retro_chirp.wav"
            strike_path = temp_dir / "cyber_lightning_strike.wav"
            arc_path = temp_dir / "cyber_lightning_arc.wav"
            zap_path = temp_dir / "cyber_lightning_zap.wav"
            drop_path = temp_dir / "cyber_teleport_drop.wav"
            target_path = temp_dir / "cyber_target_acquired.wav"
            data_rip_path = temp_dir / "cyber_data_rip.wav"
            voice_start_path = temp_dir / "cyber_voice_start.wav"
            voice_success_path = temp_dir / "cyber_voice_success.wav"
            voice_cancel_path = temp_dir / "cyber_voice_cancel.wav"
            core_destabilize_path = temp_dir / "cyber_core_destabilize.wav"

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
            if not voice_start_path.exists():
                _generate_voice_start_wav(voice_start_path)
            if not voice_success_path.exists():
                _generate_voice_success_wav(voice_success_path)
            if not voice_cancel_path.exists():
                _generate_voice_cancel_wav(voice_cancel_path)
            if not core_destabilize_path.exists():
                _generate_core_destabilize_wav(core_destabilize_path)

            self._swoosh_path = swoosh_path
            self._close_path = close_path
            self._chirp_path = chirp_path
            self._lightning_strike_path = strike_path
            self._lightning_arc_path = arc_path
            self._lightning_zap_path = zap_path
            self._teleport_drop_path = drop_path
            self._target_acquired_path = target_path
            self._data_rip_path = data_rip_path
            self._voice_start_path = voice_start_path
            self._voice_success_path = voice_success_path
            self._voice_cancel_path = voice_cancel_path
            self._core_destabilize_path = core_destabilize_path

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

            v_start_sfx = QSoundEffect(self)
            v_start_sfx.setSource(QUrl.fromLocalFile(str(voice_start_path)))
            v_start_sfx.setVolume(self._volume * 0.85)
            self._voice_start_effect = v_start_sfx

            v_succ_sfx = QSoundEffect(self)
            v_succ_sfx.setSource(QUrl.fromLocalFile(str(voice_success_path)))
            v_succ_sfx.setVolume(self._volume * 0.85)
            self._voice_success_effect = v_succ_sfx

            v_canc_sfx = QSoundEffect(self)
            v_canc_sfx.setSource(QUrl.fromLocalFile(str(voice_cancel_path)))
            v_canc_sfx.setVolume(self._volume * 0.8)
            self._voice_cancel_effect = v_canc_sfx

            core_destab_sfx = QSoundEffect(self)
            core_destab_sfx.setSource(QUrl.fromLocalFile(str(core_destabilize_path)))
            core_destab_sfx.setVolume(self._volume * 0.8)
            self._core_destabilize_effect = core_destab_sfx

            # Генерация и пул эмоциональных звуков речи
            self._chirp_paths_by_style = {}
            self._chirp_pools_by_style = {}
            self._chirp_indices_by_style = {}
            styles = ("normal", "exclamation", "question", "ellipsis")
            for st in styles:
                st_path = temp_dir / f"cyber_chirp_{st}.wav"
                if not st_path.exists():
                    _generate_chirp_wav(st_path, style=st)
                self._chirp_paths_by_style[st] = st_path
                st_pool: list[QSoundEffect] = []
                st_url = QUrl.fromLocalFile(str(st_path))
                for _ in range(3):
                    eff = QSoundEffect(self)
                    eff.setSource(st_url)
                    eff.setVolume(self._volume * (0.85 if st == "exclamation" else 0.7))
                    st_pool.append(eff)
                self._chirp_pools_by_style[st] = st_pool
                self._chirp_indices_by_style[st] = 0

            self._chirp_pool = self._chirp_pools_by_style.get("normal", [])
            self._chirp_path = self._chirp_paths_by_style.get("normal", chirp_path)

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
        if (
            hasattr(self, "_voice_start_effect")
            and self._voice_start_effect is not None
        ):
            self._voice_start_effect.setVolume(self._volume * 0.85)
        if (
            hasattr(self, "_voice_success_effect")
            and self._voice_success_effect is not None
        ):
            self._voice_success_effect.setVolume(self._volume * 0.85)
        if (
            hasattr(self, "_voice_cancel_effect")
            and self._voice_cancel_effect is not None
        ):
            self._voice_cancel_effect.setVolume(self._volume * 0.8)
        if (
            hasattr(self, "_core_destabilize_effect")
            and self._core_destabilize_effect is not None
        ):
            self._core_destabilize_effect.setVolume(self._volume * 0.8)
        for effect in self._session_effects.values():
            effect.setVolume(self._volume * 0.85)
        for pool in self._chirp_pools_by_style.values():
            for effect in pool:
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

    def play_voice_start(self) -> None:
        """Звук активации голосового прослушивания."""
        if not self.is_speech_sound_enabled():
            return
        self._play_file(
            getattr(self, "_voice_start_path", None),
            getattr(self, "_voice_start_effect", None),
        )

    def play_voice_success(self) -> None:
        """Звук успешного распознавания команды."""
        if not self.is_speech_sound_enabled():
            return
        self._play_file(
            getattr(self, "_voice_success_path", None),
            getattr(self, "_voice_success_effect", None),
        )

    def play_voice_cancel(self) -> None:
        """Звук отмены/сброса голосового ожидания."""
        if not self.is_speech_sound_enabled():
            return
        self._play_file(
            getattr(self, "_voice_cancel_path", None),
            getattr(self, "_voice_cancel_effect", None),
        )

    def play_core_destabilize(self) -> None:
        """Звук перегрузки и нарастающего напряжения ядра."""
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_core_destabilize_path", None),
            getattr(self, "_core_destabilize_effect", None),
        )

    def play_session_action(self, action: str) -> None:
        if not self.is_effects_sound_enabled():
            return
        path = self._session_paths.get(action)
        self._play_file(path, self._session_effects.get(action))

    def play_chirp(self, char: str = "") -> None:
        """Воспроизводит фонетический импульс печати с учетом пунктуации."""
        if not self.is_speech_sound_enabled():
            return
        now = time.monotonic()
        if now - self._last_chirp_time < self._throttle_interval:
            return
        self._last_chirp_time = now

        # Определение стиля звучания по текущему символу
        style = "normal"
        if char in ("!", "¡"):
            style = "exclamation"
        elif char in ("?", "¿"):
            style = "question"
        elif char in (".", "…", "-", "—"):
            style = "ellipsis"

        pool = self._chirp_pools_by_style.get(style) or self._chirp_pool
        path = self._chirp_paths_by_style.get(style) or self._chirp_path
        if not pool or path is None:
            return

        idx = self._chirp_indices_by_style.get(style, 0)
        fallback = pool[idx]
        self._chirp_indices_by_style[style] = (idx + 1) % len(pool)

        self._play_file(path, fallback)

    def stop_all(self, timeout: float = 0.3) -> None:
        pass


class _SpeechSFXHolder:
    instance: SpeechSFX | None = None


def get_speech_sfx() -> SpeechSFX:
    if _SpeechSFXHolder.instance is None:
        _SpeechSFXHolder.instance = SpeechSFX()
    return _SpeechSFXHolder.instance
