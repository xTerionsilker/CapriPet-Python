from __future__ import annotations

from .ai import OllamaAskCommand
from .base import BaseCommand, CommandContext, CommandResult
from .media import (
    SpotifyNextCommand,
    SpotifyPauseCommand,
    SpotifyPlayCommand,
    SpotifyPreviousCommand,
    SpotifyResumeCommand,
)
from .pet_actions import (
    GlitchToggleCommand,
    LocateMouseCommand,
    VoiceToggleCommand,
)
from .registry import CommandRegistry, switch_layout
from .system import (
    LockScreenCommand,
    PowerOffCommand,
    RebootCommand,
    SuspendCommand,
)
from .web import GoogleSearchCommand, YouTubeSearchCommand

DEFAULT_COMMAND_CLASSES: tuple[type[BaseCommand], ...] = (
    GlitchToggleCommand,
    VoiceToggleCommand,
    GoogleSearchCommand,
    YouTubeSearchCommand,
    SpotifyPlayCommand,
    SpotifyPauseCommand,
    SpotifyResumeCommand,
    SpotifyNextCommand,
    SpotifyPreviousCommand,
    LockScreenCommand,
    PowerOffCommand,
    SuspendCommand,
    RebootCommand,
    OllamaAskCommand,
    LocateMouseCommand,
)


def register_default_commands(registry: CommandRegistry) -> None:
    """Регистрирует все стандартные команды питомца в реестре."""
    for cls in DEFAULT_COMMAND_CLASSES:
        registry.register(cls())


def create_default_registry(
    context: CommandContext | None = None,
) -> CommandRegistry:
    """Создаёт и возвращает реестр с зарегистрированными стандартными командами."""
    registry = CommandRegistry(context=context)
    register_default_commands(registry)
    return registry


__all__ = [
    "BaseCommand",
    "CommandContext",
    "CommandResult",
    "CommandRegistry",
    "switch_layout",
    "register_default_commands",
    "create_default_registry",
    "DEFAULT_COMMAND_CLASSES",
    "GlitchToggleCommand",
    "VoiceToggleCommand",
    "GoogleSearchCommand",
    "YouTubeSearchCommand",
    "SpotifyPlayCommand",
    "SpotifyPauseCommand",
    "SpotifyResumeCommand",
    "SpotifyNextCommand",
    "SpotifyPreviousCommand",
    "LockScreenCommand",
    "PowerOffCommand",
    "SuspendCommand",
    "RebootCommand",
    "OllamaAskCommand",
    "LocateMouseCommand",
]
