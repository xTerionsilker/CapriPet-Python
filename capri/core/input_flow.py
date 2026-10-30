from __future__ import annotations

import re
from typing import Any, Callable

from PySide6.QtCore import QObject, QTimer

from .commands import switch_layout

CONFIRM_TIMEOUT_MS = 15_000
YOUTUBE_SELECT_TIMEOUT_MS = 25_000

NUMBER_WORDS_MAP: dict[str, int] = {
    "1": 1,
    "один": 1,
    "одинн": 1,
    "первый": 1,
    "первое": 1,
    "первую": 1,
    "первая": 1,
    "номер один": 1,
    "2": 2,
    "два": 2,
    "второй": 2,
    "второе": 2,
    "вторую": 2,
    "вторая": 2,
    "номер два": 2,
    "3": 3,
    "три": 3,
    "третий": 3,
    "третье": 3,
    "третью": 3,
    "третья": 3,
    "номер три": 3,
    "4": 4,
    "четыре": 4,
    "четвертый": 4,
    "четвёртый": 4,
    "четвертое": 4,
    "четвёртое": 4,
    "четвертую": 4,
    "четвёртую": 4,
    "четвертая": 4,
    "четвёртая": 4,
    "номер четыре": 4,
    "5": 5,
    "пять": 5,
    "пятый": 5,
    "пятое": 5,
    "пятую": 5,
    "пятая": 5,
    "номер пять": 5,
}

AFFIRMATIVE_WORDS = frozenset(
    {
        "да",
        "ага",
        "верно",
        "точно",
        "конечно",
        "давай",
        "подтверждаю",
        "запускай",
        "выполняй",
        "включай",
        "угу",
        "ес",
        "йес",
        "yes",
        "y",
        "ok",
        "окей",
        "ок",
    }
)
NEGATIVE_WORDS = frozenset(
    {
        "нет",
        "не",
        "неа",
        "нету",
        "отмена",
        "отменить",
        "отменяй",
        "ноу",
        "no",
        "nope",
    }
)


def _answer_words(text: str) -> set[str]:
    words = set(re.findall(r"[\w-]+", text.casefold()))
    words |= {switch_layout(w) for w in words}
    return words


def _parse_selected_number(text: str, max_number: int = 5) -> int | None:
    """Извлекает номер выбора (1..max_number) из произнесённого текста."""
    clean = " ".join(text.casefold().split())
    if clean in NUMBER_WORDS_MAP:
        num = NUMBER_WORDS_MAP[clean]
        if 1 <= num <= max_number:
            return num

    # Проверка отдельных слов и переключений раскладки
    words = _answer_words(text)
    for w in words:
        if w in NUMBER_WORDS_MAP:
            num = NUMBER_WORDS_MAP[w]
            if 1 <= num <= max_number:
                return num
    return None


def _confirm_prompt(command: Any) -> str:
    if hasattr(command, "get_confirmation_prompt"):
        return command.get_confirmation_prompt()
    description = getattr(command, "description", "").rstrip(". ")
    return f"Подтверди: «{command.name}» — {description}. (да / нет)"


class InputFlow(QObject):

    def __init__(
        self, registry: Any, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        self._pending: tuple[Any, str] | None = None
        self._custom_waiter: tuple[Callable[[str], str], QTimer] | None = None

        self._confirm_timer = QTimer(self)
        self._confirm_timer.setSingleShot(True)
        self._confirm_timer.timeout.connect(self.clear)

    @property
    def awaiting_reply(self) -> bool:
        return self._pending is not None or self._custom_waiter is not None

    def expect_reply(
        self, handler: Callable[[str], str], timeout_ms: int = CONFIRM_TIMEOUT_MS
    ) -> None:
        """Регистрирует кастомное ожидание ответа пользователя (без префикса «Капри»)."""
        self.clear()
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self.clear)
        self._custom_waiter = (handler, timer)
        timer.start(timeout_ms)

    def handle(self, text: str) -> str:
        if self._custom_waiter is not None:
            handler, timer = self._custom_waiter
            timer.stop()
            self._custom_waiter = None
            words = _answer_words(text)
            if words & NEGATIVE_WORDS:
                return "Отменено."
            return handler(text)

        if self._pending is not None:
            words = _answer_words(text)
            if words & NEGATIVE_WORDS:
                self.clear()
                return "Отменено."
            if words & AFFIRMATIVE_WORDS:
                command, original = self._pending
                self.clear()
                return self._run(command, original)
            self.clear()

        exact = self._registry.exact_match(text)
        if exact is not None:
            command, _argument = exact
            if getattr(command, "requires_confirmation", False):
                self._pending = (command, text)
                self._confirm_timer.start(CONFIRM_TIMEOUT_MS)
                return _confirm_prompt(command)
            reply = self._registry.dispatch(text)
            if reply is not None:
                return reply

        suggestion = self._registry.suggest(text)
        if suggestion is not None:
            self._pending = (suggestion, text)
            self._confirm_timer.start(CONFIRM_TIMEOUT_MS)
            return f"Ты имел в виду: «{suggestion.name}»? (да / нет)"
        return f"Ты сказал: {text}"

    def clear(self) -> None:
        self._pending = None
        if self._custom_waiter is not None:
            _, timer = self._custom_waiter
            timer.stop()
            self._custom_waiter = None
        self._confirm_timer.stop()

    def _run(self, command: Any, original: str) -> str:
        if getattr(command, "takes_argument", False):
            reply = self._registry.dispatch(f"{command.name} {original}")
        else:
            reply = self._registry.dispatch(command.name)
        return reply if reply is not None else "Готово."

