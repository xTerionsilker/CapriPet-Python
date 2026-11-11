"""Standard built-in command implementations for CapriPet.

This module re-exports domain-specific commands from submodules:
- apps: LaunchAppCommand, KillAppCommand
- debug: DebugCommand, GlitchToggleCommand, LocateMouseCommand, UpdateCommand, ConsoleCommand
- media: Spotify commands
- system: LockScreenCommand, PowerOffCommand, SuspendCommand, RebootCommand, CleanSystemCommand, RegistryCommand
- volume: VolumeUpCommand, VolumeDownCommand, VolumeSetCommand, VolumeMuteCommand, VolumeUnmuteCommand
- web: GoogleSearchCommand, YouTubeSearchCommand
"""

from __future__ import annotations

from .apps import KillAppCommand, LaunchAppCommand
from .debug import (
    ConsoleCommand,
    DebugCommand,
    GlitchToggleCommand,
    LocateMouseCommand,
    UpdateCommand,
    _describe_vosk,
    format_duration,
)
from .media import (
    SpotifyCurrentTrackCommand,
    SpotifyNextCommand,
    SpotifyPauseCommand,
    SpotifyPlayCommand,
    SpotifyPreviousCommand,
    SpotifyResumeCommand,
)
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
    _extract_volume_number,
)
from .web import GoogleSearchCommand, YouTubeSearchCommand

__all__ = [
    "CleanSystemCommand",
    "ConsoleCommand",
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
    "UpdateCommand",
    "VolumeDownCommand",
    "VolumeMuteCommand",
    "VolumeSetCommand",
    "VolumeUnmuteCommand",
    "VolumeUpCommand",
    "YouTubeSearchCommand",
    "_describe_vosk",
    "_extract_volume_number",
    "format_duration",
]
