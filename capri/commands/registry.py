from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Callable

from ..core.fuzzy import MAX_TYPO_DISTANCE, edit_distance, keyword_score, similarity
from .base import BaseCommand, CommandContext

ARGUMENT_PUNCTUATION = " \t,.:;–-!?()[]{}«»…\""

_EN_KEYS = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
_RU_KEYS = "йцукенгшщзхъфывапролджэячсмитьбю.ё"
_LAYOUT_TRANSLATION = str.maketrans(_EN_KEYS + _RU_KEYS, _RU_KEYS + _EN_KEYS)


def switch_layout(text: str) -> str:
    """Переключает раскладку текста между en (QWERTY) и ru (ЙЦУКЕН)."""
    return text.translate(_LAYOUT_TRANSLATION)


class FunctionalCommand(BaseCommand):
    """Адаптер для функциональных обработчиков (обратная совместимость)."""

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        aliases: tuple[str, ...] = (),
        keywords: tuple[str, ...] = (),
        takes_argument: bool = False,
        requires_confirmation: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.handler = handler
        self.aliases = tuple(aliases)
        self.keywords = tuple(keywords)
        self.takes_argument = takes_argument
        self.requires_confirmation = requires_confirmation

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if self.takes_argument:
            return self.handler(query)
        return self.handler()


class CommandRegistry:
    """Центральный реестр команд с поддержкой нечеткого поиска и контекста."""

    def __init__(self, context: CommandContext | None = None) -> None:
        self._commands: list[BaseCommand] = []
        self._lookup: dict[str, BaseCommand] = {}
        self._context: CommandContext | None = context

    @property
    def context(self) -> CommandContext | None:
        return self._context

    @context.setter
    def context(self, value: CommandContext | None) -> None:
        self._context = value

    def set_context(self, context: CommandContext | None) -> None:
        self._context = context

    def register(
        self,
        command_or_name: BaseCommand | str | None = None,
        description: str = "",
        handler: Callable[..., Any] | None = None,
        *,
        name: str = "",
        aliases: tuple[str, ...] = (),
        takes_argument: bool = False,
        keywords: tuple[str, ...] = (),
        requires_confirmation: bool = False,
    ) -> BaseCommand:
        """Регистрирует команду либо как BaseCommand, либо по сигнатуре (name, description, handler)."""
        if isinstance(command_or_name, BaseCommand):
            command = command_or_name
        else:
            cmd_name = command_or_name if isinstance(command_or_name, str) else name
            if not cmd_name or handler is None:
                raise ValueError("Необходимо указать имя команды и обработчик")
            command = FunctionalCommand(
                name=cmd_name,
                description=description,
                handler=handler,
                aliases=aliases,
                keywords=keywords,
                takes_argument=takes_argument,
                requires_confirmation=requires_confirmation,
            )

        keys = (command.name, *command.aliases)
        for key in keys:
            normalized = self._normalize(key)
            if normalized in self._lookup:
                raise ValueError(f"Повторяющаяся команда: {key!r}")
        for key in keys:
            self._lookup[self._normalize(key)] = command
        self._commands.append(command)
        return command

    def find(self, text: str) -> BaseCommand | None:
        match = self.match(text)
        return match[0] if match is not None else None

    def dispatch(
        self, text: str, context: CommandContext | None = None
    ) -> str | None:
        match = self.match(text)
        if match is None:
            return None
        command, argument = match
        ctx = context or self._context

        if hasattr(command, "execute"):
            if ctx is None and not isinstance(command, FunctionalCommand):
                raise RuntimeError(
                    f"Команда '{command.name}' требует CommandContext для выполнения"
                )
            return command.execute(ctx, argument)  # type: ignore
        elif hasattr(command, "handler"):
            # Обратная совместимость с dataclass Command
            h = getattr(command, "handler")
            if getattr(command, "takes_argument", False):
                return h(argument)
            return h()
        return None

    def match(self, text: str) -> tuple[BaseCommand, str] | None:
        normalized = self._normalize(text)
        if not normalized:
            return None

        exact = self._lookup.get(normalized)
        if exact is not None:
            return exact, ""

        argument_match = self._argument_match(normalized)
        if argument_match is not None:
            return argument_match

        switched = switch_layout(normalized)
        if switched != normalized:
            exact_switched = self._lookup.get(switched)
            if exact_switched is not None:
                return exact_switched, ""
            arg_switched = self._argument_match(switched)
            if arg_switched is not None:
                return arg_switched

        closest = self._closest(normalized)
        if closest is not None:
            return self._lookup[closest], ""

        if switched != normalized:
            closest_switched = self._closest(switched)
            if closest_switched is not None:
                return self._lookup[closest_switched], ""

        return None

    def exact_match(self, text: str) -> tuple[BaseCommand, str] | None:
        normalized = self._normalize(text)
        if not normalized:
            return None

        exact = self._lookup.get(normalized)
        if exact is not None:
            return exact, ""

        arg_match = self._argument_match(normalized)
        if arg_match is not None:
            return arg_match

        switched = switch_layout(normalized)
        if switched != normalized:
            exact_switched = self._lookup.get(switched)
            if exact_switched is not None:
                return exact_switched, ""
            return self._argument_match(switched)

        return None

    def suggest(self, text: str) -> BaseCommand | None:
        normalized = self._normalize(text)
        if not normalized:
            return None

        switched = switch_layout(normalized)
        queries = (normalized, switched) if switched != normalized else (normalized,)

        best: BaseCommand | None = None
        best_score: tuple[float, float] | None = None
        for command in self._commands:
            keys = (command.name, *command.aliases)
            closest = max(
                similarity(q, self._normalize(key))
                for q in queries
                for key in keys
            )
            score = max(
                closest,
                max(keyword_score(q, command.keywords) for q in queries),
            )
            candidate = (score, closest)
            if best_score is None or candidate > best_score:
                best_score = candidate
                best = command
        return best

    def _argument_match(self, normalized: str) -> tuple[BaseCommand, str] | None:
        keys = sorted(
            (
                (key, command)
                for key, command in self._lookup.items()
                if getattr(command, "takes_argument", False)
            ),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        for key, command in keys:
            if normalized == key:
                return command, ""
            if not normalized.startswith(key):
                continue
            rest = normalized[len(key) :]
            if rest[:1].isalnum():
                continue
            return command, rest.lstrip(ARGUMENT_PUNCTUATION)
        return None

    def _closest(self, normalized: str) -> str | None:
        limit = min(
            MAX_TYPO_DISTANCE, max(1, len(normalized) // 5)
        )
        best_key: str | None = None
        best_score: tuple[int, float] | None = None

        for key in self._lookup:
            distance = edit_distance(normalized, key)
            if distance > limit:
                continue
            ratio = SequenceMatcher(None, normalized, key).ratio()
            score = (distance, -ratio)
            if best_score is None or score < best_score:
                best_score = score
                best_key = key

        return best_key

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.casefold().strip(" .!?«»\"").split())

    @property
    def commands(self) -> list[BaseCommand]:
        return list(self._commands)
