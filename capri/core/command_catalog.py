from __future__ import annotations

from dataclasses import dataclass

from .command_definitions import COMMAND_DEFINITIONS
from .commands import CommandRegistry, Handler


@dataclass(frozen=True)
class Handlers:
    toggle_glitches: Handler
    toggle_voice: Handler
    ask_ollama: Handler
    search_google: Handler
    search_youtube: Handler
    spotify_play: Handler
    spotify_pause: Handler
    spotify_resume: Handler
    spotify_next: Handler
    spotify_previous: Handler
    lock_screen: Handler
    power_off: Handler
    suspend: Handler
    reboot: Handler
    locate_mouse: Handler


def register_commands(registry: CommandRegistry, handlers: Handlers) -> None:
    for cmd in COMMAND_DEFINITIONS:
        handler = getattr(handlers, cmd["handler_attr"])
        registry.register(
            name=cmd["name"],
            description=cmd["description"],
            handler=handler,
            aliases=cmd.get("aliases", ()),
            keywords=cmd.get("keywords", ()),
            takes_argument=cmd.get("takes_argument", False),
            requires_confirmation=cmd.get("requires_confirmation", False),
        )
