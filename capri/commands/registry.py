from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz

from ..core.fuzzy import MAX_TYPO_DISTANCE, edit_distance, keyword_score, similarity
from ..core.morphology import normalize_spoken_numbers, stem_russian_word, stem_text
from .base import BaseCommand, CommandContext

ARGUMENT_PUNCTUATION = " \t,.:;–-!?()[]{}«»…\""

_EN_KEYS = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
_RU_KEYS = "йцукенгшщзхъфывапролджэячсмитьбю.ё"
_LAYOUT_TRANSLATION = str.maketrans(_EN_KEYS + _RU_KEYS, _RU_KEYS + _EN_KEYS)


def switch_layout(text: str) -> str:
    """Переключает раскладку текста между en (QWERTY) и ru (ЙЦУКЕН)."""
    return text.translate(_LAYOUT_TRANSLATION)


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

    def register(self, command: BaseCommand) -> BaseCommand:
        """Регистрирует команду BaseCommand в реестре."""
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
        normalized = self._normalize(text)
        if not normalized:
            return None

        exact = self._lookup.get(normalized)
        if exact is not None:
            return exact, ""

        argument_match = self._argument_match(normalized)
        if argument_match is not None:
            return argument_match

        # Проверка с нормализацией числительных (например, 'громкость пятьдесят' -> 'громкость 50')
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

        # Морфологический (стемминг) поиск без аргументов
        stemmed_match = self._stemmed_match(normalized)
        if stemmed_match is not None:
            return stemmed_match

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

        # Отсекаем ложные подсказки при низком сходстве
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

        # Перестановка слов / Поиск ключевого действия в любой позиции фразы
        # Выбираем ключ с максимальным числом совпавших слов
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
        limit = min(
            MAX_TYPO_DISTANCE, max(1, len(normalized) // 5)
        )
        best_key: str | None = None
        best_score: tuple[int, float] | None = None

        for key in self._lookup:
            distance = edit_distance(normalized, key)
            if distance > limit:
                continue
            ratio = fuzz.ratio(normalized, key) / 100.0
            score = (distance, -ratio)
            if best_score is None or score < best_score:
                best_score = score
                best_key = key

        return best_key

    def _stemmed_match(self, normalized: str) -> tuple[BaseCommand, str] | None:
        """Матчит команду на основе стемминга корней слов."""
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
