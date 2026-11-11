"""Координатор пасхалок и глитч-розыгрышей оцифрованного конструкта личности Capri."""

from __future__ import annotations

import random
import time
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

ALL_PRANK_TYPES: tuple[str, ...] = ("dodge", "melt", "relic_dump")


class EngramPrankCoordinator(QObject):
    """Центральный координатор вероятностей, кулдаунов и анти-повторов пасхалок энграммы."""

    sig_trigger_dodge = Signal(int)  # hops_count
    sig_trigger_melt = Signal()
    sig_trigger_relic_dump = Signal(str)  # variant: "terminal" | "bubble"

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cooldown_until: float = 0.0
        self._last_prank: str | None = None
        self._is_prank_active: bool = False

        # Защитные колбэки (Safety Gates)
        self._check_game_active: Callable[[], bool] = self._default_game_check
        self._check_shredding: Callable[[], bool] = lambda: False
        self._check_recording: Callable[[], bool] = lambda: False

    @staticmethod
    def _default_game_check() -> bool:
        try:
            from ..integrations.game_mode import GameModeDetector

            return bool(GameModeDetector().is_game_active)
        except Exception:
            return False

    @property
    def last_prank(self) -> str | None:
        return self._last_prank

    @property
    def is_prank_active(self) -> bool:
        return self._is_prank_active

    def set_prank_active(self, active: bool) -> None:
        self._is_prank_active = active

    def set_game_active_checker(self, checker: Callable[[], bool]) -> None:
        self._check_game_active = checker

    def set_shredding_checker(self, checker: Callable[[], bool]) -> None:
        self._check_shredding = checker

    def set_recording_checker(self, checker: Callable[[], bool]) -> None:
        self._check_recording = checker

    def is_cooldown_active(self) -> bool:
        return time.monotonic() < self._cooldown_until

    def arm_cooldown(self, min_sec: int = 480, max_sec: int = 720) -> None:
        duration = random.randint(min_sec, max_sec)
        self._cooldown_until = time.monotonic() + duration

    def clear_cooldown(self) -> None:
        self._cooldown_until = 0.0

    def can_trigger_prank(self) -> bool:
        """Проверяет все условия готовности к запуску розыгрыша."""
        if self._is_prank_active:
            return False
        if self.is_cooldown_active():
            return False
        if self._check_game_active():
            return False
        if self._check_shredding():
            return False
        if self._check_recording():
            return False
        return True

    def get_available_prank_types(self) -> list[str]:
        """Возвращает список доступных типов с учётом фильтра анти-повтора."""
        candidates = [p for p in ALL_PRANK_TYPES if p != self._last_prank]
        return candidates if candidates else list(ALL_PRANK_TYPES)

    def on_pet_appeared(self) -> bool:
        """Обрабатывает появление/пробуждение Капри через двухступенчатый фильтр.

        Ступень 1: Шанс 60% (0.60).
        Ступень 2: Равновероятный выбор из доступных кандидатов без повтора подряд.
        Возвращает True, если была запущена пасхалка.
        """
        if not self.can_trigger_prank():
            return False

        # Ступень 1: 60% шанс на запуск пасхалки
        if random.random() >= 0.60:
            return False

        # Ступень 2: Выбор конкретного розыгрыша
        candidates = self.get_available_prank_types()
        chosen = random.choice(candidates)
        self._last_prank = chosen
        self.arm_cooldown()

        if chosen == "dodge":
            hops = random.randint(2, 3)
            self.sig_trigger_dodge.emit(hops)
        elif chosen == "melt":
            self.sig_trigger_melt.emit()
        elif chosen == "relic_dump":
            variant = "terminal" if random.random() < 0.5 else "bubble"
            self.sig_trigger_relic_dump.emit(variant)

        return True
