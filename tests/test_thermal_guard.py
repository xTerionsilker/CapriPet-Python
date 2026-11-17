"""Тесты для термомониторинга и защитного механизма ThermalGuard."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from capri.integrations.thermal_guard import ThermalGuard


class TestThermalGuard(unittest.TestCase):
    """Набор тестов для ThermalGuard."""

    def test_query_nvidia_smi_success(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="65.4\n",
            )
            guard = ThermalGuard()
            temp = guard.get_gpu_temperature()
            self.assertEqual(temp, 65.4)

    def test_query_nvidia_smi_failure_soft_skip(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            guard = ThermalGuard()
            # Без nvidia-smi и без wmi должен вернуть None без исключений
            temp = guard.get_gpu_temperature()
            self.assertIsNone(temp)

    def test_overheat_detection_window(self) -> None:
        guard = ThermalGuard(temp_limit_celsius=78, overheat_duration_sec=2.0)

        with patch.object(guard, "get_gpu_temperature", return_value=82.0):
            with patch("time.monotonic", side_effect=[100.0, 101.0, 102.5]):
                # 1-й опрос: зафиксировано превышение, таймер стартовал, но длительность < 2.0с
                self.assertFalse(guard.check_overheat())
                # 2-й опрос: прошло 1.0с < 2.0с
                self.assertFalse(guard.check_overheat())
                # 3-й опрос: прошло 2.5с >= 2.0с -> критический перегрев
                self.assertTrue(guard.check_overheat())

    def test_temp_stabilization_resets_overheat(self) -> None:
        guard = ThermalGuard(temp_limit_celsius=78, overheat_duration_sec=2.0)

        with patch.object(guard, "get_gpu_temperature") as mock_temp:
            with patch("time.monotonic", return_value=100.0):
                mock_temp.return_value = 82.0
                self.assertFalse(guard.check_overheat())
                self.assertIsNotNone(guard._overheat_start_time)

                # Температура упала до безопасной
                mock_temp.return_value = 70.0
                self.assertFalse(guard.check_overheat())
                self.assertIsNone(guard._overheat_start_time)


if __name__ == "__main__":
    unittest.main()
