from __future__ import annotations

import array
import math


class EnergyVAD:
    """Адаптивный детектор речевой активности (VAD).

    Отслеживает уровень фонового шума с фильтрацией импульсных помех
    (кликов мыши, стука клавиатуры) и автоматически подстраивает порог речи.
    """

    def __init__(
        self,
        sample_rate: int = 16_000,
        initial_noise_rms: float = 120.0,
        min_speech_threshold: float = 300.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.noise_floor = initial_noise_rms
        self.min_speech_threshold = min_speech_threshold
        self._history: list[float] = []

    def reset(self, initial_noise_rms: float = 120.0) -> None:
        self.noise_floor = initial_noise_rms
        self._history.clear()

    @staticmethod
    def calculate_rms(chunk: bytes) -> float:
        if len(chunk) < 2:
            return 0.0
        usable = len(chunk) - (len(chunk) % 2)
        samples = array.array("h")
        samples.frombytes(chunk[:usable])
        if not samples:
            return 0.0
        total = sum(s * s for s in samples)
        return math.sqrt(total / len(samples))

    def is_speech(self, chunk: bytes) -> tuple[bool, float]:
        """Определяет, содержит ли чанк речь, и возвращает (is_speech, rms_level)."""
        rms = self.calculate_rms(chunk)
        if rms <= 0.0:
            return False, 0.0

        speech_threshold = max(self.min_speech_threshold, self.noise_floor * 2.2)

        # Если уровень явно ниже порога речи — плавно обновляем шумовой фон
        if rms < speech_threshold:
            self.noise_floor = self.noise_floor * 0.95 + rms * 0.05
            is_active = False
        else:
            # Для отсева ультракоротких импульсных щелчков мыши (кликов)
            is_active = True

        return is_active, rms
