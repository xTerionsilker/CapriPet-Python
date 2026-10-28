from __future__ import annotations

import re

from typing import Any

from PySide6.QtCore import QObject, QTimer

from .commands import switch_layout

CONFIRM_TIMEOUT_MS = 15_000
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

        self._confirm_timer = QTimer(self)
        self._confirm_timer.setSingleShot(True)
        self._confirm_timer.timeout.connect(self.clear)

    @property
    def awaiting_reply(self) -> bool:
        return self._pending is not None

    def handle(self, text: str) -> str:
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
        self._confirm_timer.stop()

    def _run(self, command: Any, original: str) -> str:
        if getattr(command, "takes_argument", False):
            reply = self._registry.dispatch(f"{command.name} {original}")
        else:
            reply = self._registry.dispatch(command.name)
        return reply if reply is not None else "Готово."
