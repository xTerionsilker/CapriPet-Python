"""Разбор ввода пользователя: подтверждение, команды, эхо.

Пока Capri ждёт ответа «да» / «нет» на предложенную команду, следующая
фраза считается ответом (``CONFIRM_TIMEOUT_MS``). В остальных случаях
фраза проходит через реестр: точное совпадение выполняется сразу, а всё
остальное «притягивается» к самой похожей команде и требует подтверждения.

Это весь «мозг» Capri: окно ``capri.pet_window`` лишь передаёт сюда текст
и показывает возвращённую строку. Свою логику можно подставить вместо
``InputFlow.handle`` в ``CapriWindow.process_input``.

Использование::

    flow = InputFlow(CommandRegistry(), parent=window)
    reply = flow.handle("загугли котиков")
"""

from __future__ import annotations

import re

from PySide6.QtCore import QObject, QTimer

from .commands import Command, CommandRegistry

# Сколько ждём ответ «да» / «нет» на предложенную команду.
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
        "no",
        "nope",
    }
)


def _answer_words(text: str) -> set[str]:
    """Слова фразы, чтобы распознать «да» / «нет» среди других слов."""
    return set(re.findall(r"[\w-]+", text.casefold()))


class InputFlow(QObject):
    """Превращает строку пользователя в ответ, при необходимости спрашивая."""

    def __init__(
        self, registry: CommandRegistry, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        # Команда, предложенная для нераспознанной фразы. Пока она ждёт
        # ответа «да» / «нет», следующая фраза считается подтверждением.
        self._pending: tuple[Command, str] | None = None

        self._confirm_timer = QTimer(self)
        self._confirm_timer.setSingleShot(True)
        self._confirm_timer.timeout.connect(self.clear)

    @property
    def awaiting_reply(self) -> bool:
        """Ждёт ли Capri «да» / «нет» на предложенную команду."""
        return self._pending is not None

    def handle(self, text: str) -> str:
        """Обработать строку пользователя и вернуть ответ Capri."""
        # Сначала проверяем ответ на предложенную команду.
        if self._pending is not None:
            words = _answer_words(text)
            if words & NEGATIVE_WORDS:
                self.clear()
                return "Отменено."
            if words & AFFIRMATIVE_WORDS:
                command, original = self._pending
                self.clear()
                return self._run(command, original)
            # Не «да» и не «нет» — считаем это новой фразой.
            self.clear()

        # Точные команды (включая команды с аргументом) выполняются сразу.
        if self._registry.exact_match(text) is not None:
            reply = self._registry.dispatch(text)
            if reply is not None:
                return reply

        # Любую другую фразу «притягиваем» к самой похожей команде и
        # обязательно спрашиваем подтверждение.
        suggestion = self._registry.suggest(text)
        if suggestion is not None:
            self._pending = (suggestion, text)
            self._confirm_timer.start(CONFIRM_TIMEOUT_MS)
            return f"Ты имел в виду: «{suggestion.name}»? (да / нет)"
        return f"Ты сказал: {text}"

    def clear(self) -> None:
        """Забыть предложенную команду и остановить таймер ожидания."""
        self._pending = None
        self._confirm_timer.stop()

    # --- внутреннее --------------------------------------------------------
    def _run(self, command: Command, original: str) -> str:
        """Выполнить подтверждённую команду."""
        if command.takes_argument:
            reply = self._registry.dispatch(f"{command.name} {original}")
        else:
            reply = self._registry.dispatch(command.name)
        return reply if reply is not None else "Готово."
