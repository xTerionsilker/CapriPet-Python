from __future__ import annotations

from rapidfuzz import process
from rapidfuzz.distance import DamerauLevenshtein

from ..core.morphology import normalize_spoken_numbers, stem_text
from ..core.wake_word import MAX_TYPO_DISTANCE, keyword_score, similarity
from .base import BaseCommand, CommandContext

ARGUMENT_PUNCTUATION = " \t,.:;–-!?()[]{}«»…\""

_EN_KEYS = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
_RU_KEYS = "йцукенгшщзхъфывапролджэячсмитьбю.ё"
_LAYOUT_TRANSLATION = str.maketrans(_EN_KEYS + _RU_KEYS, _RU_KEYS + _EN_KEYS)


def switch_layout(text: str) -> str:
    return text.translate(_LAYOUT_TRANSLATION)


_EN_COMMAND_PREFIXES: dict[str, str] = {
    "pause": "пауза",
    "stop": "пауза",
    "play": "продолжить",
    "resume": "продолжить",
    "next": "следующий трек",
    "next track": "следующий трек",
    "skip": "следующий трек",
    "prev": "предыдущий трек",
    "previous": "предыдущий трек",
    "previous track": "предыдущий трек",
    "open": "запусти",
    "launch": "запусти",
    "run": "запусти",
    "start": "запусти",
    "close": "убей",
    "kill": "убей",
    "exit": "убей",
    "lock": "блокировка",
    "lock screen": "блокировка",
    "sleep": "сон",
    "reboot": "перезагрузка",
    "restart": "перезагрузка",
    "shutdown": "выключи",
    "power off": "выключи",
    "status": "дебаг",
    "debug": "дебаг",
    "info": "дебаг",
    "glitch": "глитч",
    "glitches": "глитч",
    "spotify": "спотифай",
    "google": "гугл",
    "youtube": "ютуб",
    "where mouse": "где мышь",
    "where is mouse": "где мышь",
    "where is cursor": "где мышь",
    "what is playing": "что играет",
    "what's playing": "что играет",
    "update": "обновление",
}


def normalize_english_command(text: str) -> str:
    clean = text.strip()
    lower = clean.lower()

    if lower in _EN_COMMAND_PREFIXES:
        return _EN_COMMAND_PREFIXES[lower]

    for prefix in sorted(_EN_COMMAND_PREFIXES, key=len, reverse=True):
        if lower.startswith(prefix + " ") or lower.startswith(prefix + ":"):
            rest = clean[len(prefix):].lstrip(" :,\t")
            ru_prefix = _EN_COMMAND_PREFIXES[prefix]
            return f"{ru_prefix} {rest}" if rest else ru_prefix

    return clean


class CommandRegistry:
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

    def register(self, command: BaseCommand) -> BaseCommand:
        if not isinstance(command, BaseCommand):
            raise TypeError(f"Ожидается BaseCommand, получено {type(command).__name__}")

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

        if ctx is None:
            raise RuntimeError(
                f"Команда '{command.name}' требует CommandContext для выполнения"
            )
        return command.execute(ctx, argument)

    def match(self, text: str) -> tuple[BaseCommand, str] | None:
        text = normalize_english_command(text)
        normalized = self._normalize(text)
        if not normalized:
            return None

        exact = self._lookup.get(normalized)
        if exact is not None:
            return exact, ""

        argument_match = self._argument_match(normalized)
        if argument_match is not None:
            return argument_match

        with_numbers = normalize_spoken_numbers(normalized)
        if with_numbers != normalized:
            arg_num = self._argument_match(with_numbers)
            if arg_num is not None:
                return arg_num

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

        stemmed_match = self._stemmed_match(normalized)
        if stemmed_match is not None:
            return stemmed_match

        return None

    def exact_match(self, text: str) -> tuple[BaseCommand, str] | None:
        text = normalize_english_command(text)
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

    def suggest(self, text: str, min_confidence: float = 0.65) -> BaseCommand | None:
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

        if best_score is not None and best_score[0] < min_confidence:
            return None

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
            if normalized.startswith(key):
                rest = normalized[len(key) :]
                if not rest[:1].isalnum():
                    return command, normalize_spoken_numbers(rest.lstrip(ARGUMENT_PUNCTUATION))

        words = normalized.split()
        best_perm_match: tuple[BaseCommand, str] | None = None
        best_perm_len = 0

        for key, command in keys:
            key_words = key.split()
            if len(key_words) > 1 and len(words) > len(key_words):
                if all(kw in words for kw in key_words):
                    indices = [words.index(kw) for kw in key_words]
                    remaining = [w for i, w in enumerate(words) if i not in indices]
                    if remaining and len(key_words) > best_perm_len:
                        best_perm_len = len(key_words)
                        arg_str = normalize_spoken_numbers(" ".join(remaining))
                        best_perm_match = (command, arg_str)

        if best_perm_match is not None:
            return best_perm_match

        return None

    def _closest(self, normalized: str) -> str | None:
        limit = min(MAX_TYPO_DISTANCE, max(1, len(normalized) // 5))
        match = process.extractOne(
            normalized,
            self._lookup.keys(),
            scorer=DamerauLevenshtein.distance,
            score_cutoff=limit,
        )
        return match[0] if match is not None else None

    def _stemmed_match(self, normalized: str) -> tuple[BaseCommand, str] | None:
        stemmed_input = stem_text(normalized)
        for command in self._commands:
            for alias in (command.name, *command.aliases):
                if stem_text(self._normalize(alias)) == stemmed_input:
                    return command, ""
        return None

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.casefold().strip(" .!?«»\"").split())

    @property
    def commands(self) -> list[BaseCommand]:
        return list(self._commands)
