"""Command subsystem package exports and default command registry wiring."""

from __future__ import annotations

from .apps import KillAppCommand, LaunchAppCommand
from .base import BaseCommand, CommandContext, CommandResult
from .debug import (
    ConsoleCommand,
    DebugCommand,
    GlitchToggleCommand,
    LocateMouseCommand,
    UpdateCommand,
)
from .media import (
    SpotifyCurrentTrackCommand,
    SpotifyNextCommand,
    SpotifyPauseCommand,
    SpotifyPlayCommand,
    SpotifyPreviousCommand,
    SpotifyResumeCommand,
)
from .registry import CommandRegistry, switch_layout
from .system import (
    CleanSystemCommand,
    LockScreenCommand,
    PowerOffCommand,
    RebootCommand,
    RegistryCommand,
    SuspendCommand,
)
from .volume import (
    VolumeDownCommand,
    VolumeMuteCommand,
    VolumeSetCommand,
    VolumeUnmuteCommand,
    VolumeUpCommand,
)
from .web import GoogleSearchCommand, YouTubeSearchCommand

DEFAULT_COMMAND_CLASSES: tuple[type[BaseCommand], ...] = (
    ConsoleCommand,
    DebugCommand,
    CleanSystemCommand,
    RegistryCommand,
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
    VolumeUpCommand,
    VolumeDownCommand,
    VolumeSetCommand,
    VolumeMuteCommand,
    VolumeUnmuteCommand,
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
    "DEFAULT_COMMAND_CLASSES",
    "BaseCommand",
    "CleanSystemCommand",
    "CommandContext",
    "CommandRegistry",
    "CommandResult",
    "DebugCommand",
    "GlitchToggleCommand",
    "GoogleSearchCommand",
    "KillAppCommand",
    "LaunchAppCommand",
    "LocateMouseCommand",
    "LockScreenCommand",
    "PowerOffCommand",
    "RebootCommand",
    "RegistryCommand",
    "SpotifyCurrentTrackCommand",
    "SpotifyNextCommand",
    "SpotifyPauseCommand",
    "SpotifyPlayCommand",
    "SpotifyPreviousCommand",
    "SpotifyResumeCommand",
    "SuspendCommand",
    "VolumeDownCommand",
    "VolumeMuteCommand",
    "VolumeSetCommand",
    "VolumeUnmuteCommand",
    "VolumeUpCommand",
    "YouTubeSearchCommand",
    "create_default_registry",
    "register_default_commands",
    "switch_layout",
]
