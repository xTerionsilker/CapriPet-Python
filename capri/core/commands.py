from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher

from .fuzzy import MAX_TYPO_DISTANCE, edit_distance, keyword_score, similarity

Handler = Callable[..., str]

HELP_ALIASES = (
    "помощь",
    "что ты умеешь?",
    "что умеешь?",
    "команды",
    "справка",
    "помоги",
    "возможности",
    "меню",
)

ARGUMENT_PUNCTUATION = " \t,.:;–-!?()[]{}«»…\""


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: Handler
    aliases: tuple[str, ...] = ()
    takes_argument: bool = False
    keywords: tuple[str, ...] = ()
    requires_confirmation: bool = False


class CommandRegistry:

    def __init__(self) -> None:
        self._commands: list[Command] = []
        self._lookup: dict[str, Command] = {}
        self._help = Command(
            "помощь",
            "показать этот список.",
            self.help_text,
            HELP_ALIASES,
            keywords=("помощ", "умеешь", "справк", "возможност", "команд"),
        )
        for key in HELP_ALIASES:
            self._lookup[self._normalize(key)] = self._help

    def register(
        self,
        name: str,
        description: str,
        handler: Handler,
        *,
        aliases: tuple[str, ...] = (),
        takes_argument: bool = False,
        keywords: tuple[str, ...] = (),
        requires_confirmation: bool = False,
    ) -> Command:
        command = Command(
            name,
            description,
            handler,
            tuple(aliases),
            takes_argument,
            tuple(keywords),
            requires_confirmation,
        )
        keys = (name, *aliases)
        for key in keys:
            normalized = self._normalize(key)
            if normalized in self._lookup:
                raise ValueError(f"Повторяющаяся команда: {key!r}")
        for key in keys:
            self._lookup[self._normalize(key)] = command
        self._commands.append(command)
        return command

    def find(self, text: str) -> Command | None:
        match = self.match(text)
        return match[0] if match is not None else None

    def dispatch(self, text: str) -> str | None:
        match = self.match(text)
        if match is None:
            return None
        command, argument = match
        if command.takes_argument:
            return command.handler(argument)
        return command.handler()

    def match(self, text: str) -> tuple[Command, str] | None:
        normalized = self._normalize(text)
        if not normalized:
            return None

        exact = self._lookup.get(normalized)
        if exact is not None:
            return exact, ""

        argument_match = self._argument_match(normalized)
        if argument_match is not None:
            return argument_match

        closest = self._closest(normalized)
        if closest is not None:
            return self._lookup[closest], ""
        return None

    def exact_match(self, text: str) -> tuple[Command, str] | None:
        normalized = self._normalize(text)
        if not normalized:
            return None

        exact = self._lookup.get(normalized)
        if exact is not None:
            return exact, ""

        return self._argument_match(normalized)

    def suggest(self, text: str) -> Command | None:
        normalized = self._normalize(text)
        if not normalized:
            return None

        best: Command | None = None
        best_score: tuple[float, float] | None = None
        for command in (*self._commands, self._help):
            keys = (command.name, *command.aliases)
            closest = max(
                similarity(normalized, self._normalize(key)) for key in keys
            )
            score = max(closest, keyword_score(normalized, command.keywords))
            candidate = (score, closest)
            if best_score is None or candidate > best_score:
                best_score = candidate
                best = command
        return best

    def help_text(self) -> str:
        lines = [
            "Доступные команды:",
            "• помощь (также: что ты умеешь?) — показать этот список.",
        ]
        for command in self._commands:
            argument = " <запрос>" if command.takes_argument else ""
            aliases = (
                f" (также: {', '.join(command.aliases)})"
                if command.aliases
                else ""
            )
            lines.append(
                f"• {command.name}{argument}{aliases} — {command.description}"
            )
        return "\n".join(lines)

    def _argument_match(self, normalized: str) -> tuple[Command, str] | None:
        keys = sorted(
            (
                (key, command)
                for key, command in self._lookup.items()
                if command.takes_argument
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
