"""Автоматизированные тесты для Issue #4: контекстно-адаптивная телеметрия процессов."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QCoreApplication

from capri.core.process_classifier import (
    DEFAULT_CATEGORY_PHRASES,
    DEFAULT_PROCESS_CATEGORIES,
    ProcessClassifier,
)
from capri.core.settings import CapriConfig, TelemetryConfig


class TestProcessClassifier(unittest.TestCase):
    """Тестирование семантического классификатора процессов."""

    def setUp(self) -> None:
        self.classifier = ProcessClassifier()

    def test_default_categories(self) -> None:
        self.assertEqual(self.classifier.classify("code.exe"), "dev")
        self.assertEqual(self.classifier.classify("pycharm64.exe"), "dev")
        self.assertEqual(self.classifier.classify("chrome.exe"), "web")
        self.assertEqual(self.classifier.classify("firefox.exe"), "web")
        self.assertEqual(self.classifier.classify("spotify.exe"), "media")
        self.assertEqual(self.classifier.classify("excel.exe"), "corpo")
        self.assertEqual(self.classifier.classify("blender.exe"), "heavy")
        self.assertIsNone(self.classifier.classify("unknown_app_123.exe"))

    def test_case_insensitivity(self) -> None:
        self.assertEqual(self.classifier.classify("Code.EXE"), "dev")
        self.assertEqual(self.classifier.classify("CHROME.EXE"), "web")

    def test_custom_rules(self) -> None:
        custom = {"notepad.exe": "corpo", "custom_game.exe": "heavy"}
        classifier = ProcessClassifier(custom_rules=custom)
        self.assertEqual(classifier.classify("notepad.exe"), "corpo")
        self.assertEqual(classifier.classify("custom_game.exe"), "heavy")
        # Дефолтные правила также должны работать
        self.assertEqual(classifier.classify("code.exe"), "dev")

    def test_phrase_generation(self) -> None:
        for cat in ("dev", "web", "media", "corpo", "heavy"):
            phrase = self.classifier.get_reaction_phrase(cat)
            self.assertIsInstance(phrase, str)
            self.assertTrue(len(phrase) > 10)
            self.assertIn(phrase, DEFAULT_CATEGORY_PHRASES[cat])


class TestTelemetryConfig(unittest.TestCase):
    """Тестирование валидации конфигурации телеметрии."""

    def test_defaults(self) -> None:
        cfg = CapriConfig()
        self.assertTrue(cfg.telemetry.process_monitoring_enabled)
        self.assertEqual(cfg.telemetry.foreground_poll_ms, 1000)
        self.assertEqual(cfg.telemetry.background_scan_interval_sec, 8.0)
        self.assertEqual(cfg.telemetry.category_cooldown_sec, 240)
        self.assertEqual(cfg.telemetry.global_cooldown_sec, 30)
        self.assertEqual(cfg.telemetry.custom_rules, {})

    def test_custom_values(self) -> None:
        data = {
            "telemetry": {
                "process_monitoring_enabled": False,
                "category_cooldown_sec": 120,
                "custom_rules": {"test.exe": "dev"},
            }
        }
        cfg = CapriConfig.model_validate(data)
        self.assertFalse(cfg.telemetry.process_monitoring_enabled)
        self.assertEqual(cfg.telemetry.category_cooldown_sec, 120)
        self.assertEqual(cfg.telemetry.custom_rules, {"test.exe": "dev"})


class TestProcessWatcher(unittest.TestCase):
    """Тестирование контроллера ProcessWatcher."""

    @classmethod
    def setUpClass(cls) -> None:
        # Для работы сигналов и таймеров Qt требуется QCoreApplication
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_cooldown_and_signals(self) -> None:
        from capri.controllers.process_watcher import ProcessWatcher

        emitted_events: list[tuple[str, str, str]] = []

        is_game = False
        watcher = ProcessWatcher(is_game_active=lambda: is_game)
        # Уменьшаем кулдауны для быстрого тестирования
        watcher._global_cooldown_sec = 0.5
        watcher._category_cooldown_sec = 1.0

        watcher.sig_process_context_changed.connect(
            lambda cat, app, phr: emitted_events.append((cat, app, phr))
        )

        # 1. Первый триггер (dev -> code.exe)
        watcher._evaluate_trigger("code.exe", is_foreground=True)
        self.assertEqual(len(emitted_events), 1)
        self.assertEqual(emitted_events[0][0], "dev")
        self.assertEqual(emitted_events[0][1], "code.exe")

        # 2. Немедленный повторный триггер (блокируется глобальным дебаунсом)
        watcher._evaluate_trigger("chrome.exe", is_foreground=True)
        self.assertEqual(len(emitted_events), 1, "Глобальный дебаунс должен блокировать быстрый спам")

        # 3. В игровом режиме реплики полностью подавляются
        is_game = True
        watcher._last_global_time = 0.0  # Сбрасываем таймер для теста
        watcher._evaluate_trigger("chrome.exe", is_foreground=True)
        self.assertEqual(len(emitted_events), 1, "Игровой режим должен блокировать любые реплики")

    def test_orchestrator_game_mode_property_compatibility(self) -> None:
        from capri.integrations.game_mode import GameModeDetector
        from capri.controllers.orchestrator import PetOrchestrator

        # Проверка, что GameModeDetector.is_game_active является property
        self.assertTrue(isinstance(getattr(GameModeDetector, "is_game_active"), property))

        # Создаем мок окна с детектором
        mock_window = MagicMock()
        mock_detector = MagicMock()
        mock_detector.is_game_active = True  # property возвращает bool
        mock_window._game_detector = mock_detector

        # Тестируем метод _is_game_active в изоляции
        orch_is_game = PetOrchestrator._is_game_active(MagicMock(_window=mock_window))
        self.assertTrue(orch_is_game)

        mock_detector.is_game_active = False
        orch_is_game = PetOrchestrator._is_game_active(MagicMock(_window=mock_window))
        self.assertFalse(orch_is_game)


if __name__ == "__main__":
    unittest.main()
