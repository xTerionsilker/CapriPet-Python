"""External platform and system service integrations package exports."""

from __future__ import annotations

from . import (
    app_launcher,
    discord_rpc,
    process_manager,
    registry_scanner,
    spotify,
    system_cleaner,
    system_control,
    system_power_hook,
    system_volume,
    web_search,
    window_tracker,
)

__all__ = [
    "app_launcher",
    "discord_rpc",
    "process_manager",
    "registry_scanner",
    "spotify",
    "system_cleaner",
    "system_control",
    "system_power_hook",
    "system_volume",
    "web_search",
    "window_tracker",
]
