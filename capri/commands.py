"""Небольшой реестр команд для текстового и голосового ввода Capri.

Команды регистрируются с одним или несколькими псевдонимами. Реестр также
обрабатывает неявную команду ``помощь`` / ``что ты умеешь?``, которая
перечисляет всё, что сейчас доступно.

Сопоставление снисходительное: пунктуация, регистр и лишние пробелы
игнорируются, а небольшие опечатки принимаются, если ввод отличается от
известной команды на несколько правок. Число допустимых правок растёт с
длиной команды.

Пример::

    from capri.commands import CommandRegistry

    registry = CommandRegistry()
    registry.register(
        "танец",
        "заставить Capri танцевать.",
        lambda: "Capri танцует!",
        aliases=("начать танец",),
    )

    registry.dispatch("помощь")      # -> список команд
    registry.dispatch("начать танец") # -> "Capri танцует!"
    registry.dispatch("нет")          # -> None
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher

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

# Длинный ввод может содержать больше опечаток: одна правка до 5 символов,
# затем ещё одна на каждые 5 символов, с ограничением, чтобы посторонние
# фразы никогда не совпадали с командой.
_MAX_TYPO_DISTANCE = 3


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: Handler
    aliases: tuple[str, ...] = ()
    takes_argument: bool = False


class CommandRegistry:
    """Сопоставляет ввод с обработчиками и описывает все команды."""

    def __init__(self) -> None:
        self._commands: list[Command] = []
        self._lookup: dict[str, Command] = {}
        # ``помощь`` неявная: у неё есть настоящая Command, чтобы её находил
        # и точный, и нечёткий поиск, но в ``_commands`` её нет, чтобы она не
        # выводилась дважды.
        self._help = Command(
            "помощь", "показать этот список.", self.help_text, HELP_ALIASES
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
    ) -> Command:
        command = Command(
            name, description, handler, tuple(aliases), takes_argument
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
        """Вернуть подходящую команду, допуская небольшие опечатки."""
        match = self.match(text)
        return match[0] if match is not None else None

    def dispatch(self, text: str) -> str | None:
        """Выполнить подходящую команду и вернуть ответ, либо ``None``."""
        match = self.match(text)
        if match is None:
            return None
        command, argument = match
        if command.takes_argument:
            return command.handler(argument)
        return command.handler()

    def match(self, text: str) -> tuple[Command, str] | None:
        """Найти команду и остаток строки, переданный как аргумент.

        Команды без аргументов ищутся по всей строке, в том числе нечётко.
        Команды с аргументом (поиск) срабатывают, если строка начинается с
        имени или псевдонима, за которым идёт запрос.
        """
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

    def help_text(self) -> str:
        """Вернуть понятный список всех доступных команд."""
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

    # --- внутреннее --------------------------------------------------------
    def _argument_match(self, normalized: str) -> tuple[Command, str] | None:
        """Сопоставить команду с аргументом по самому длинному префиксу."""
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
            if normalized.startswith(key + " "):
                return command, normalized[len(key) :].strip()
        return None

    def _closest(self, normalized: str) -> str | None:
        """Вернуть ближайший известный ключ, если он достаточно близок."""
        limit = min(
            _MAX_TYPO_DISTANCE, max(1, len(normalized) // 5)
        )
        best_key: str | None = None
        best_score: tuple[int, float] | None = None

        for key in self._lookup:
            distance = _edit_distance(normalized, key)
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


def _edit_distance(left: str, right: str) -> int:
    """Расстояние оптимального выравнивания (Левенштейн + перестановки)."""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    # Три скользящих ряда: [i-2], [i-1], [i].
    prev_prev = [0] * (len(right) + 1)
    prev = list(range(len(right) + 1))

    for i, left_char in enumerate(left, start=1):
        current = [i] + [0] * len(right)
        for j, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            current[j] = min(
                prev[j] + 1,          # удаление
                current[j - 1] + 1,   # вставка
                prev[j - 1] + cost,   # замена
            )
            if (
                i > 1
                and j > 1
                and left_char == right[j - 2]
                and left[i - 2] == right_char
            ):
                current[j] = min(current[j], prev_prev[j - 2] + 1)
        prev_prev, prev = prev, current

    return prev[-1]
