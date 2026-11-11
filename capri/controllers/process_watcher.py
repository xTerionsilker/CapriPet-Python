"""Контроллер мониторинга активных и фоновых процессов Windows (ProcessWatcher).

Обеспечивает гибридную телеметрию: моментальное определение активного окна (foreground)
через Win32 API и периодический срез ресурсоемких фоновых задач через psutil.
"""

from __future__ import annotations

import ctypes
import logging
import os
import time
from collections.abc import Callable
from ctypes import wintypes
from typing import Any

import psutil
from PySide6.QtCore import QObject, QTimer, Signal

from ..core.process_classifier import ProcessClassifier
from ..core.settings import get_config_value

logger = logging.getLogger(__name__)

# Инициализация Win32 User32
user32: Any
try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None


class ProcessWatcher(QObject):
    """Асинхронный контроллер отслеживания процессов и смены рабочего контекста хоста."""

    sig_process_context_changed = Signal(str, str, str)  # (category, app_name, phrase)

    def __init__(
        self,
        is_game_active: Callable[[], bool] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._is_game_active = is_game_active or (lambda: False)
        self._own_pid = os.getpid()

        # Загрузка настроек телеметрии
        self._enabled: bool = bool(
            get_config_value("telemetry.process_monitoring_enabled", True)
        )
        self._foreground_poll_ms: int = int(
            get_config_value("telemetry.foreground_poll_ms", 1000)
        )
        self._background_interval_sec: float = float(
            get_config_value("telemetry.background_scan_interval_sec", 8.0)
        )
        self._category_cooldown_sec: float = float(
            get_config_value("telemetry.category_cooldown_sec", 240.0)
        )
        self._global_cooldown_sec: float = float(
            get_config_value("telemetry.global_cooldown_sec", 30.0)
        )
        custom_rules: dict[str, str] = dict(
            get_config_value("telemetry.custom_rules", {})
        )

        self._classifier = ProcessClassifier(custom_rules)

        # Состояние трекинга
        self._current_foreground_app: str | None = None
        self._last_global_time: float = 0.0
        self._last_category_time: dict[str, float] = {}
        self._seen_background_heavy: set[str] = set()

        # Таймеры Qt
        self._foreground_timer = QTimer(self)
        self._foreground_timer.setInterval(self._foreground_poll_ms)
        self._foreground_timer.timeout.connect(self._poll_foreground_window)

        self._background_timer = QTimer(self)
        self._background_timer.setInterval(int(self._background_interval_sec * 1000))
        self._background_timer.timeout.connect(self._poll_background_processes)

    def start(self) -> None:
        """Запускает сенсорные таймеры мониторинга."""
        if not self._enabled:
            return
        if user32:
            self._foreground_timer.start()
        self._background_timer.start()
        logger.info("ProcessWatcher: запущен гибридный сенсорный конвейер.")

    def stop(self) -> None:
        """Останавливает таймеры мониторинга."""
        self._foreground_timer.stop()
        self._background_timer.stop()

    def set_enabled(self, enabled: bool) -> None:
        """Включает или выключает телеметрию процессов."""
        self._enabled = enabled
        if enabled:
            self.start()
        else:
            self.stop()

    def _get_foreground_process_name(self) -> str | None:
        """Извлекает имя исполняемого файла активного окна через Win32 API."""
        if not user32:
            return None
        hwnd = user32.GetForegroundWindow()
        if not hwnd or not user32.IsWindow(hwnd):
            return None
        if user32.IsIconic(hwnd):
            return None

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value or pid.value == self._own_pid:
            return None

        try:
            proc = psutil.Process(pid.value)
            return proc.name().lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

    def _poll_foreground_window(self) -> None:
        """Периодический опрос активного окна переднего плана."""
        app_name = self._get_foreground_process_name()
        if not app_name or app_name == self._current_foreground_app:
            return

        self._current_foreground_app = app_name
        self._evaluate_trigger(app_name, is_foreground=True)

    def _poll_background_processes(self) -> None:
        """Периодический срез фоновых процессов для обнаружения тяжелых задач."""
        if not self._enabled or self._is_game_active():
            return

        current_heavy: set[str] = set()
        try:
            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info.get("name")
                    if not name:
                        continue
                    name_clean = name.lower()
                    if self._classifier.classify(name_clean) == "heavy":
                        current_heavy.add(name_clean)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as ex:  # noqa: BLE001
            logger.debug("ProcessWatcher background scan error: %s", ex)
            return

        # Находим новые тяжелые процессы, которых не было на предыдущем цикле
        new_heavy = current_heavy - self._seen_background_heavy
        self._seen_background_heavy = current_heavy

        for heavy_app in new_heavy:
            self._evaluate_trigger(heavy_app, is_foreground=False)

    def _evaluate_trigger(self, app_name: str, is_foreground: bool) -> None:
        """Проверяет кулдауны и инициирует событие контекста."""
        if not self._enabled:
            return

        # 100% молчание в игровом режиме
        if self._is_game_active():
            return

        category = self._classifier.classify(app_name)
        if not category:
            return

        now = time.monotonic()

        # Глобальный дебаунс тишины (30 секунд)
        if now - self._last_global_time < self._global_cooldown_sec:
            return

        # Покатегорийный кулдаун (240 секунд)
        last_cat_time = self._last_category_time.get(category, 0.0)
        if now - last_cat_time < self._category_cooldown_sec:
            return

        phrase = self._classifier.get_reaction_phrase(category)
        self._last_global_time = now
        self._last_category_time[category] = now

        logger.info(
            "ProcessWatcher: событие контекста '%s' (%s, fg=%s)",
            category,
            app_name,
            is_foreground,
        )
        self.sig_process_context_changed.emit(category, app_name, phrase)
