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
import threading
import time
import wave
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QMediaDevices, QSoundEffect

logger = logging.getLogger(__name__)

# Master audio parameters (Studio Trigger cyber soundscape)
DEFAULT_SAMPLE_RATE: int = 44100
SFX_VERSION: str = "v6_biochip_hijack"  # Bust cache on generator update


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
    file_path: Path, sample_rate: int = 44100, duration: float = 1.10
) -> None:
    """Смертоносный локдаун: тревожная сирена перехвата, лязг затвора и статика."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(2024)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        # 1. Тяжелая тревожная двухтональная сирена изоляции (sweep 420-880 Hz)
        siren_phase = math.sin(2.0 * math.pi * 3.8 * t)
        siren_freq = 520.0 + 340.0 * (0.5 + 0.5 * siren_phase)
        siren_env = min(1.0, t / 0.08) * max(0.0, 1.0 - p * 0.45)
        siren = (
            0.50 * math.sin(2.0 * math.pi * siren_freq * t)
            + 0.25 * math.tanh(math.sin(2.0 * math.pi * siren_freq * 1.5 * t) * 2.5)
        ) * siren_env

        # 2. Гидравлический лязг барьера оцепления на 0.35s
        clank = 0.0
        if 0.34 <= t < 0.55:
            cp = (t - 0.34) / 0.21
            clank_freq = 210.0 * math.exp(-4.5 * cp)
            clank_env = (1.0 - cp) ** 2.2
            clank = (
                0.60 * math.sin(2.0 * math.pi * clank_freq * t)
                + 0.35 * rng.uniform(-1.0, 1.0) * clank_env
            )

        # 3. Финальный подтверждающий щелчок блокировки на 0.75s
        snap = 0.0
        if 0.74 <= t < 0.88:
            sp = (t - 0.74) / 0.14
            snap_env = math.sin(math.pi * sp) ** 1.8
            snap = (
                0.45 * math.sin(2.0 * math.pi * 1760.0 * t)
                + 0.30 * math.sin(2.0 * math.pi * 2640.0 * t)
            ) * snap_env

        val = _pack_sample(siren + clank + snap, drive=1.35, master_gain=0.92)
        frames.extend(val)

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_session_power_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 1.30
) -> None:
    """Разрыв нейросвязи: кинетический импульс, затухающий спад катушек и схлопывание ЭЛТ."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(404)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        # 1. Начальный высоковольтный импульс разрыва нейролинка (0.00 - 0.15s)
        zap = 0.0
        if t < 0.15:
            zp = t / 0.15
            zap_env = (1.0 - zp) ** 1.5
            zap = (
                0.70 * math.sin(2.0 * math.pi * (3400.0 - 2600.0 * zp) * t)
                + 0.40 * rng.uniform(-1.0, 1.0)
            ) * zap_env

        # 2. Гул падающего напряжения и разряда мощных конденсаторов
        spool_freq = 180.0 * math.exp(-3.2 * p)
        spool_env = (1.0 - p) ** 0.85
        spool = (
            0.50 * math.sin(2.0 * math.pi * spool_freq * t)
            + 0.25 * math.tanh(math.sin(2.0 * math.pi * spool_freq * 2.0 * t) * 2.0)
        ) * spool_env

        # 3. Финальный хлопок схлопывания ЭЛТ-луча в точку (0.85 - 1.25s)
        crt_pop = 0.0
        if 0.85 <= t < 1.25:
            cp = (t - 0.85) / 0.40
            crt_freq = 60.0 * math.exp(-6.0 * cp)
            crt_pop = (
                0.60 * math.sin(2.0 * math.pi * crt_freq * t)
                + 0.20 * rng.uniform(-1.0, 1.0) * (1.0 - cp) ** 2.0
            ) * math.sin(math.pi * cp)

        val = _pack_sample(zap + spool + crt_pop, drive=1.40, master_gain=0.94)
        frames.extend(val)

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_session_suspend_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 1.25
) -> None:
    """Криостазис: глубокий суб-басовый гул, затухающие гармоники и медленный кардио-импульс."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        # 1. Глубокое дыхание крио-камеры (низкочастотный суб-бас 55-45 Hz)
        sub_freq = 55.0 - 15.0 * p
        breath = math.sin(2.0 * math.pi * sub_freq * t)

        # 2. Холодный эмбиентный пэд в тональности ре-минор
        pad = (
            0.35 * math.sin(2.0 * math.pi * 146.83 * t)
            + 0.25 * math.sin(2.0 * math.pi * 220.0 * t)
            + 0.15 * math.sin(2.0 * math.pi * 293.66 * t)
        ) * (0.6 + 0.4 * math.sin(2.0 * math.pi * 1.2 * t))

        # 3. Редкий затухающий пульс биочипа на 0.25s и 0.70s
        pulse = 0.0
        for center_t in (0.25, 0.70):
            if abs(t - center_t) < 0.06:
                diff = (t - center_t) / 0.06
                pulse += 0.28 * math.sin(2.0 * math.pi * 880.0 * t) * (1.0 - diff * diff)

        fade = min(1.0, t / 0.10) * max(0.0, (1.0 - p) ** 1.3)
        val = _pack_sample((breath * 0.45 + pad * 0.40 + pulse * 0.35) * fade, drive=1.20, master_gain=0.90)
        frames.extend(val)

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_session_reboot_wav(
    file_path: Path, sample_rate: int = 44100, duration: float = 1.20
) -> None:
    """Цикл буйного перезапуска: восходящий разгон шин памяти, щелчки реле и росчерки молний."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(777)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        # 1. Восходящий турбо-разгон шины данных (pitch bend 120 -> 1800 Hz)
        spool_freq = 120.0 + 1680.0 * (p**2.2)
        spool = 0.45 * math.sin(2.0 * math.pi * spool_freq * t)

        # 2. Быстрые триггерные арпеджио и пакеты данных
        burst = 0.0
        if 0.20 <= t < 0.75:
            step = int((t - 0.20) * 16.0)
            note_freq = 330.0 * (1.25 ** (step % 6))
            burst = 0.35 * math.sin(2.0 * math.pi * note_freq * t)

        # 3. Электрический щелчок реле и перегрузка Acid Green на 0.85s
        relay = 0.0
        if 0.82 <= t < 0.98:
            rp = (t - 0.82) / 0.16
            relay = (
                0.60 * math.sin(2.0 * math.pi * 180.0 * t)
                + 0.40 * rng.uniform(-1.0, 1.0)
            ) * math.sin(math.pi * rp)

        val = _pack_sample(spool + burst + relay, drive=1.45, master_gain=0.92)
        frames.extend(val)

    _write_wav_16bit(file_path, frames, sample_rate)


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


def _generate_relay_snap_wav(
    file_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE, duration: float = 0.08
) -> None:
    """Щелчок аппаратного электромагнитного реле / разряда конденсатора при смене аудио-регистра."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(77)
    for i in range(num_samples):
        t = i / sample_rate
        p = t / duration

        # Быстрый экспоненциальный спад
        env = math.exp(-32.0 * p)
        # Высокочастотный металлический щелчок контакта (3400 Гц)
        snap = math.sin(2.0 * math.pi * 3400.0 * t) * 0.6
        # Механический глухой стук сердечника реле (210 Гц)
        thud = math.sin(2.0 * math.pi * 210.0 * t) * 0.4
        # Микро-искра размыкания контакта в начале импульса
        spark = rng.uniform(-0.5, 0.5) if p < 0.2 else 0.0

        val = (snap + thud + spark) * env
        frames.extend(_pack_sample(val, drive=1.8, master_gain=0.90))

    _write_wav_16bit(file_path, frames, sample_rate)


def _generate_intro_breach_wav(
    file_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE, duration: float = 4.5
) -> None:
    """Кинематографичный саундтрек взлома биочипа: BIOS-клики, сирена тревоги, суб-басовый удар и кибер-аккорд."""
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    rng = random.Random(101)
    for i in range(num_samples):
        t = i / sample_rate
        if t < 1.0:
            hum = math.sin(2.0 * math.pi * 55.0 * t) * 0.08
            tick_t = t % 0.18
            tick = math.sin(2.0 * math.pi * 1400.0 * tick_t) * math.exp(-65.0 * tick_t) if tick_t < 0.04 else 0.0
            val = hum + tick * 0.35
            frames.extend(_pack_sample(val, drive=1.5, master_gain=0.75))
        elif t < 1.8:
            t_alarm = t - 1.0
            lfo = math.sin(2.0 * math.pi * 8.0 * t_alarm) * 350.0
            siren = math.sin(2.0 * math.pi * (6500.0 + lfo) * t_alarm) * 0.5 + math.sin(2.0 * math.pi * (7200.0 - lfo) * t_alarm) * 0.3
            pulse = 0.5 + 0.5 * math.sin(2.0 * math.pi * 4.0 * t_alarm)
            env = min(1.0, t_alarm / 0.3)
            val = siren * pulse * env + rng.uniform(-0.15, 0.15) * env
            frames.extend(_pack_sample(val, drive=2.6, master_gain=0.88))
        elif t < 2.6:
            t_snap = t - 1.8
            freq = 28.0 + 57.0 * math.exp(-10.0 * t_snap)
            sub = math.sin(2.0 * math.pi * freq * t_snap) * math.exp(-5.0 * t_snap)
            electric = math.sin(2.0 * math.pi * 2400.0 * t_snap) * rng.uniform(-0.6, 0.6) * math.exp(-12.0 * t_snap)
            val = sub * 1.3 + electric * 0.4
            frames.extend(_pack_sample(val, drive=3.2, master_gain=0.98))
        else:
            t_cyber = t - 2.6
            p = min(1.0, t_cyber / 1.9)
            env = max(0.0, 1.0 - p) ** 1.3
            chord = (
                math.sin(2.0 * math.pi * 659.25 * t_cyber) * 0.35
                + math.sin(2.0 * math.pi * 880.00 * t_cyber) * 0.30
                + math.sin(2.0 * math.pi * 1318.5 * t_cyber) * 0.20
            ) * env
            val = chord + math.sin(2.0 * math.pi * 42.0 * t_cyber) * 0.15 * env
            frames.extend(_pack_sample(val, drive=1.4, master_gain=0.80))

    _write_wav_16bit(file_path, frames, sample_rate)


def _ensure_wav_cache_sync(temp_dir: Path) -> None:
    """Генерирует отсутствующие процедурные WAV файлы в кэше."""
    try:
        temp_dir.mkdir(parents=True, exist_ok=True)
        jobs = [
            (temp_dir / "cyber_swoosh.wav", lambda p: _generate_swoosh_wav(p)),
            (temp_dir / "cyber_close.wav", lambda p: _generate_close_wav(p)),
            (temp_dir / "retro_chirp.wav", lambda p: _generate_chirp_wav(p)),
            (temp_dir / "cyber_lightning_strike.wav", lambda p: _generate_lightning_strike_wav(p)),
            (temp_dir / "cyber_lightning_arc.wav", lambda p: _generate_lightning_arc_wav(p)),
            (temp_dir / "cyber_lightning_zap.wav", lambda p: _generate_lightning_zap_wav(p)),
            (temp_dir / "cyber_teleport_drop.wav", lambda p: _generate_teleport_drop_wav(p)),
            (temp_dir / "cyber_target_acquired.wav", lambda p: _generate_target_acquired_wav(p)),
            (temp_dir / "cyber_data_rip.wav", lambda p: _generate_data_rip_wav(p)),
            (temp_dir / "cyber_voice_start.wav", lambda p: _generate_voice_start_wav(p)),
            (temp_dir / "cyber_voice_success.wav", lambda p: _generate_voice_success_wav(p)),
            (temp_dir / "cyber_voice_cancel.wav", lambda p: _generate_voice_cancel_wav(p)),
            (temp_dir / "cyber_core_destabilize.wav", lambda p: _generate_core_destabilize_wav(p)),
            (temp_dir / "cyber_relay_snap.wav", lambda p: _generate_relay_snap_wav(p)),
            (temp_dir / "cyber_intro_breach.wav", lambda p: _generate_intro_breach_wav(p)),
            (temp_dir / "cyber_session_lock.wav", lambda p: _generate_session_lock_wav(p)),
            (temp_dir / "cyber_session_power.wav", lambda p: _generate_session_power_wav(p)),
            (temp_dir / "cyber_session_suspend.wav", lambda p: _generate_session_suspend_wav(p)),
            (temp_dir / "cyber_session_reboot.wav", lambda p: _generate_session_reboot_wav(p)),
            (temp_dir / "cyber_chirp_normal.wav", lambda p: _generate_chirp_wav(p, style="normal")),
            (temp_dir / "cyber_chirp_exclamation.wav", lambda p: _generate_chirp_wav(p, style="exclamation")),
            (temp_dir / "cyber_chirp_question.wav", lambda p: _generate_chirp_wav(p, style="question")),
            (temp_dir / "cyber_chirp_ellipsis.wav", lambda p: _generate_chirp_wav(p, style="ellipsis")),
        ]
        for path, generator in jobs:
            if not path.exists():
                generator(path)
    except (OSError, ValueError, RuntimeError) as exc:
        logger.warning("Ошибка при фоновой генерации SFX кэша: %s", exc)


def preload_sfx_cache_async() -> threading.Thread:
    """Запускает фоновый воркер предварительной генерации аудио-файлов без блокировки UI."""
    temp_dir = Path(tempfile.gettempdir()) / f"capri_sfx_{SFX_VERSION}"
    thread = threading.Thread(
        target=_ensure_wav_cache_sync,
        args=(temp_dir,),
        name="CapriSfxPreloadThread",
        daemon=True,
    )
    thread.start()
    return thread


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
            relay_snap_path = temp_dir / "cyber_relay_snap.wav"
            intro_breach_path = temp_dir / "cyber_intro_breach.wav"

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

            _ensure_wav_cache_sync(temp_dir)

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
            self._relay_snap_path = relay_snap_path
            self._intro_breach_path = intro_breach_path

            for action, (filename, _generator) in session_specs.items():
                path = temp_dir / filename
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

            relay_sfx = QSoundEffect(self)
            relay_sfx.setSource(QUrl.fromLocalFile(str(relay_snap_path)))
            relay_sfx.setVolume(self._volume * 0.9)
            self._relay_snap_effect = relay_sfx

            intro_breach_sfx = QSoundEffect(self)
            intro_breach_sfx.setSource(QUrl.fromLocalFile(str(intro_breach_path)))
            intro_breach_sfx.setVolume(self._volume * 0.95)
            self._intro_breach_effect = intro_breach_sfx

            # Пул эмоциональных звуков речи
            self._chirp_paths_by_style = {}
            self._chirp_pools_by_style = {}
            self._chirp_indices_by_style = {}
            styles = ("normal", "exclamation", "question", "ellipsis")
            for st in styles:
                st_path = temp_dir / f"cyber_chirp_{st}.wav"
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
        except (OSError, RuntimeError, ValueError) as exc:
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
        except (OSError, RuntimeError, ValueError) as exc:
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
        except (RuntimeError, OSError) as exc:
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
        if (
            hasattr(self, "_relay_snap_effect")
            and self._relay_snap_effect is not None
        ):
            self._relay_snap_effect.setVolume(self._volume * 0.9)
        if (
            hasattr(self, "_intro_breach_effect")
            and self._intro_breach_effect is not None
        ):
            self._intro_breach_effect.setVolume(self._volume * 0.95)
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

    def play_relay_snap(self) -> None:
        """Звук аппаратного переключения реле / разряда конденсатора при регулировке звука."""
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_relay_snap_path", None),
            getattr(self, "_relay_snap_effect", None),
        )

    def play_intro_breach(self) -> None:
        """Кинематографичный звук первого пробоя Blackwall (свист катушек + раскол стекла)."""
        if not self.is_effects_sound_enabled():
            return
        self._play_file(
            getattr(self, "_intro_breach_path", None),
            getattr(self, "_intro_breach_effect", None),
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
