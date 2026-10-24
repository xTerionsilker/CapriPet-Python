"""Small command registry for Capri's text input.

Commands are registered with one or more aliases. The registry also handles
the implicit ``help`` / ``what u can?`` command, which lists everything that
is currently available.

Matching is forgiving: punctuation, casing and extra whitespace are ignored,
and small typos are accepted as long as the input is within a few edits of a
known command (for example ``gltich`` or ``quie`` still work). The number of
allowed edits grows with the length of the command.

Example::

    from capri.commands import CommandRegistry

    registry = CommandRegistry()
    registry.register(
        "dance",
        "make Capri dance.",
        lambda: "Capri wiggles!",
        aliases=("start dance",),
    )

    registry.dispatch("help")        # -> command list
    registry.dispatch("start dance") # -> "Capri wiggles!"
    registry.dispatch("nope")        # -> None
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher

Handler = Callable[[], str]

HELP_ALIASES = ("help", "what u can?", "commands")

# Longer inputs may contain more typos: 1 edit up to 5 chars, then one more
# per 5 characters, capped so unrelated sentences never match a command.
_MAX_TYPO_DISTANCE = 3


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: Handler
    aliases: tuple[str, ...] = ()


class CommandRegistry:
    """Maps user input to handlers and can describe every registered command."""

    def __init__(self) -> None:
        self._commands: list[Command] = []
        self._lookup: dict[str, Command] = {}
        # ``help`` is implicit: give it a real Command so exact and fuzzy
        # lookups can both find it, but keep it out of ``_commands`` so it is
        # not listed twice.
        self._help = Command(
            "help", "show this list.", self.help_text, HELP_ALIASES
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
    ) -> Command:
        command = Command(name, description, handler, tuple(aliases))
        keys = (name, *aliases)
        for key in keys:
            normalized = self._normalize(key)
            if normalized in self._lookup:
                raise ValueError(f"Duplicate command: {key!r}")
        for key in keys:
            self._lookup[self._normalize(key)] = command
        self._commands.append(command)
        return command

    def find(self, text: str) -> Command | None:
        """Return the matching command, accepting small typos."""
        normalized = self._normalize(text)
        if not normalized:
            return None

        exact = self._lookup.get(normalized)
        if exact is not None:
            return exact

        match = self._closest(normalized)
        return self._lookup[match] if match is not None else None

    def dispatch(self, text: str) -> str | None:
        """Run the matching command and return its reply, or ``None``."""
        command = self.find(text)
        return command.handler() if command is not None else None

    def help_text(self) -> str:
        """Return a human-readable list of every available command."""
        lines = [
            "Available commands:",
            "• help (aliases: what u can?) — show this list.",
        ]
        for command in self._commands:
            aliases = (
                f" (aliases: {', '.join(command.aliases)})"
                if command.aliases
                else ""
            )
            lines.append(
                f"• {command.name}{aliases} — {command.description}"
            )
        return "\n".join(lines)

    # --- internals ---------------------------------------------------------
    def _closest(self, normalized: str) -> str | None:
        """Return the known key closest to ``normalized``, if close enough."""
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
        return " ".join(text.casefold().strip(" .!?").split())


def _edit_distance(left: str, right: str) -> int:
    """Optimal-string-alignment distance (Levenshtein + transpositions)."""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    # Three rolling rows: [i-2], [i-1], [i].
    prev_prev = [0] * (len(right) + 1)
    prev = list(range(len(right) + 1))

    for i, left_char in enumerate(left, start=1):
        current = [i] + [0] * len(right)
        for j, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            current[j] = min(
                prev[j] + 1,          # deletion
                current[j - 1] + 1,   # insertion
                prev[j - 1] + cost,   # substitution
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
