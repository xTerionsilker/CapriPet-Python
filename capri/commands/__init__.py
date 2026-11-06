from __future__ import annotations

from .base import BaseCommand, CommandContext, CommandResult
from .handlers import (
    DebugCommand,
    CleanSystemCommand,
    GlitchToggleCommand,
    GoogleSearchCommand,
    KillAppCommand,
    LaunchAppCommand,
    LocateMouseCommand,
    LockScreenCommand,
    PowerOffCommand,
    RebootCommand,
    SpotifyCurrentTrackCommand,
    SpotifyNextCommand,
    SpotifyPauseCommand,
    SpotifyPlayCommand,
    SpotifyPreviousCommand,
    SpotifyResumeCommand,
    SuspendCommand,
    UpdateCommand,
    YouTubeSearchCommand,
)
from .registry import CommandRegistry, switch_layout

DEFAULT_COMMAND_CLASSES: tuple[type[BaseCommand], ...] = (
    DebugCommand,
    CleanSystemCommand,
    GlitchToggleCommand,
    GoogleSearchCommand,
    YouTubeSearchCommand,
    UpdateCommand,
    SpotifyPlayCommand,
    SpotifyPauseCommand,
    SpotifyResumeCommand,
    SpotifyNextCommand,
    SpotifyPreviousCommand,
    SpotifyCurrentTrackCommand,
    LockScreenCommand,
    PowerOffCommand,
    SuspendCommand,
    RebootCommand,
    LocateMouseCommand,
    LaunchAppCommand,
    KillAppCommand,
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
    "DebugCommand",
    "CleanSystemCommand",
    "GlitchToggleCommand",
    "GoogleSearchCommand",
    "YouTubeSearchCommand",
    "SpotifyPlayCommand",
    "SpotifyPauseCommand",
    "SpotifyResumeCommand",
    "SpotifyNextCommand",
    "SpotifyPreviousCommand",
    "SpotifyCurrentTrackCommand",
    "LockScreenCommand",
    "PowerOffCommand",
    "SuspendCommand",
    "RebootCommand",
    "LocateMouseCommand",
    "LaunchAppCommand",
    "KillAppCommand",
]
