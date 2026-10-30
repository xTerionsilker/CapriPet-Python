from __future__ import annotations

from typing import Any, Tuple

from ..commands import DEFAULT_COMMAND_CLASSES

_CMD_TO_HANDLER: dict[str, str] = {
    "дебаг": "debug_info",
    "глитч": "toggle_glitches",
    "голос": "toggle_voice",
    "гугл": "search_google",
    "ютуб": "search_youtube",
    "обновление": "open_update_page",
    "спотифай": "spotify_play",
    "пауза": "spotify_pause",
    "продолжить": "spotify_resume",
    "следующий трек": "spotify_next",
    "предыдущий трек": "spotify_previous",
    "блокировка": "lock_screen",
    "я спать": "power_off",
    "я гулять": "suspend",
    "перезагрузка": "reboot",
    "слушай": "ask_ollama",
    "где мышь": "locate_mouse",
}


def _build_command_definitions() -> Tuple[dict[str, Any], ...]:
    defs: list[dict[str, Any]] = []
    for cls in DEFAULT_COMMAND_CLASSES:
        cmd = cls()
        item: dict[str, Any] = {
            "name": cmd.name,
            "description": cmd.description,
            "handler_attr": _CMD_TO_HANDLER.get(cmd.name, ""),
            "aliases": cmd.aliases,
            "keywords": cmd.keywords,
        }
        if cmd.takes_argument:
            item["takes_argument"] = True
        if cmd.requires_confirmation:
            item["requires_confirmation"] = True
        defs.append(item)
    return tuple(defs)


COMMAND_DEFINITIONS: Tuple[dict[str, Any], ...] = _build_command_definitions()
