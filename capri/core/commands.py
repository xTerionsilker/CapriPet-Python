from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher

from .fuzzy import MAX_TYPO_DISTANCE, edit_distance, keyword_score, similarity

Handler = Callable[..., str]

ARGUMENT_PUNCTUATION = " \t,.:;–-!?()[]{}«»…\""

_EN_KEYS = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
_RU_KEYS = "йцукенгшщзхъфывапролджэячсмитьбю.ё"
_LAYOUT_TRANSLATION = str.maketrans(_EN_KEYS + _RU_KEYS, _RU_KEYS + _EN_KEYS)


def switch_layout(text: str) -> str:
    """Переключает раскладку текста между en (QWERTY) и ru (ЙЦУКЕН)."""
    return text.translate(_LAYOUT_TRANSLATION)


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

    def exact_match(self, text: str) -> tuple[Command, str] | None:
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

    def suggest(self, text: str) -> Command | None:
        normalized = self._normalize(text)
        if not normalized:
            return None

        switched = switch_layout(normalized)
        queries = (normalized, switched) if switched != normalized else (normalized,)

        best: Command | None = None
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
