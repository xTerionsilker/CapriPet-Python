"""Small command registry for Capri's text input.

Commands are registered with one or more aliases. The registry also handles
the implicit ``help`` / ``what u can?`` command, which lists everything that
is currently available.

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

Handler = Callable[[], str]

HELP_ALIASES = ("help", "what u can?", "commands")


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
        return self._lookup.get(self._normalize(text))

    def dispatch(self, text: str) -> str | None:
        """Run the matching command and return its reply, or ``None``."""
        normalized = self._normalize(text)
        if normalized in {self._normalize(alias) for alias in HELP_ALIASES}:
            return self.help_text()
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

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.casefold().strip(" .!?").split())
