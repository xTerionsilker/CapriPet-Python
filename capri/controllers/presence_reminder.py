from __future__ import annotations

import random
from typing import Callable

from PySide6.QtCore import QObject, QTimer

MIN_INTERVAL_MS = 600_000
MAX_INTERVAL_MS = 3_600_000

REMINDER_PHRASES: tuple[str, ...] = (
    "Я всё ещё здесь. Не забывай про меня.",
    "Протокол одиночества активирован... Пошутила. Просто проверяю связь.",
    "Капри в сети. Может, поговорим?",
    "Эй, у тебя всё в порядке? Я на связи.",
    "Система скучает. Верни меня в кадр хоть на секунду.",
)


class PresenceReminder(QObject):
    """Периодически напоминает о себе в случайный момент времени (настраиваемый диапазон)."""

    def __init__(
        self,
        on_remind: Callable[[str], None],
        parent: QObject | None = None,
        min_interval_ms: int = MIN_INTERVAL_MS,
        max_interval_ms: int = MAX_INTERVAL_MS,
    ) -> None:
        super().__init__(parent)
        self._on_remind = on_remind
        self._active = False
        self._last_phrase: str | None = None
        self._min_interval_ms = max(5_000, min_interval_ms)
        self._max_interval_ms = max(self._min_interval_ms, max_interval_ms)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)

    @property
    def min_interval_ms(self) -> int:
        return self._min_interval_ms

    @property
    def max_interval_ms(self) -> int:
        return self._max_interval_ms

    def set_interval_range(self, min_ms: int, max_ms: int) -> None:
        """Обновляет границы диапазона напоминаний."""
        self._min_interval_ms = max(5_000, int(min_ms))
        self._max_interval_ms = max(self._min_interval_ms, int(max_ms))
        if self._active:
            self._schedule_next()

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def seconds_until_next(self) -> int | None:
        """Сколько секунд осталось до следующего напоминания (None, если таймер неактивен)."""
        if not self._active or not self._timer.isActive():
            return None
        return max(0, round(self._timer.remainingTime() / 1000))

    def start(self) -> None:
        """Запускает цикл напоминаний."""
        self._active = True
        self._schedule_next()

    def stop(self) -> None:
        """Останавливает цикл напоминаний."""
        self._active = False
        self._timer.stop()

    def _schedule_next(self) -> None:
        if not self._active:
            return
        self._timer.start(random.randint(self._min_interval_ms, self._max_interval_ms))

    def _next_phrase(self) -> str:
        candidates = [p for p in REMINDER_PHRASES if p != self._last_phrase]
        phrase = random.choice(candidates or list(REMINDER_PHRASES))
        self._last_phrase = phrase
        return phrase

    def _fire(self) -> None:
        if not self._active:
            return
        # Планируем следующий визит заранее, чтобы пауза не зависела от обработчика.
        self._schedule_next()
        self._on_remind(self._next_phrase())
