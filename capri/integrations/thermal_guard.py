"""Универсальный термомониторинг GPU и системных сенсоров Windows."""

from __future__ import annotations

import logging
import subprocess
import time

logger = logging.getLogger(__name__)

# Флаг для подавления окна консоли при запуске subprocess в Windows
_CREATE_NO_WINDOW = 0x08000000


class ThermalGuard:
    """Адаптивный контроллер температуры GPU с защитой от перегрева."""

    def __init__(
        self,
        temp_limit_celsius: int = 78,
        overheat_duration_sec: float = 5.0,
    ) -> None:
        self.temp_limit_celsius = temp_limit_celsius
        self.overheat_duration_sec = overheat_duration_sec
        self._overheat_start_time: float | None = None
        self._last_checked_temp: float | None = None

    def get_gpu_temperature(self) -> float | None:
        """Считывает текущую температуру GPU (NVIDIA или WMI fallback)."""
        temp = self._query_nvidia_smi()
        if temp is not None:
            self._last_checked_temp = temp
            return temp

        temp = self._query_wmi_thermal()
        self._last_checked_temp = temp
        return temp

    def check_overheat(self) -> bool:
        """Проверяет превышение лимита температуры в течение заданного окна времени.

        Returns:
            True, если температура держится выше или равна лимиту
            дольше overheat_duration_sec.
        """
        temp = self.get_gpu_temperature()
        if temp is None:
            # Датчики недоступны (soft-skip) — не блокируем работу
            self._overheat_start_time = None
            return False

        if temp >= self.temp_limit_celsius:
            now = time.monotonic()
            if self._overheat_start_time is None:
                self._overheat_start_time = now
                logger.warning(
                    "[ThermalGuard] GPU temp exceeded threshold: %.1f°C >= %d°C",
                    temp,
                    self.temp_limit_celsius,
                )
                return False

            duration = now - self._overheat_start_time
            if duration >= self.overheat_duration_sec:
                logger.error(
                    "[ThermalGuard] Critical overheat sustained: %.1f°C for %.1fs (limit %d°C)",
                    temp,
                    duration,
                    self.temp_limit_celsius,
                )
                return True
            return False

        # Температура вернулась в безопасный диапазон
        if self._overheat_start_time is not None:
            logger.info(
                "[ThermalGuard] GPU temp stabilized: %.1f°C (< %d°C)",
                temp,
                self.temp_limit_celsius,
            )
            self._overheat_start_time = None
        return False

    def reset(self) -> None:
        """Сбрасывает счетчики перегрева."""
        self._overheat_start_time = None
        self._last_checked_temp = None

    @property
    def last_temperature(self) -> float | None:
        """Последнее успешно зарегистрированное значение температуры."""
        return self._last_checked_temp

    @staticmethod
    def _query_nvidia_smi() -> float | None:
        """Запрашивает температуру через штатную утилиту nvidia-smi."""
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=1.5,
                creationflags=_CREATE_NO_WINDOW,
                check=False,
            )
            if res.returncode == 0 and res.stdout:
                line = res.stdout.strip().splitlines()[0]
                return float(line)
        except (subprocess.SubprocessError, FileNotFoundError, ValueError, IndexError):
            pass
        return None

    @staticmethod
    def _query_wmi_thermal() -> float | None:
        """Резервный опрос WMI-датчиков температуры Windows."""
        try:
            import wmi  # type: ignore[import-untyped,import-not-found]

            w = wmi.WMI(namespace="root\\wmi")
            zones = w.MSAcpi_ThermalZoneTemperature()
            if zones:
                # WMI возвращает температуру в десятых долях Кельвина
                kelvin_deci = zones[0].CurrentTemperature
                return (kelvin_deci / 10.0) - 273.15
        except Exception:
            pass
        return None
