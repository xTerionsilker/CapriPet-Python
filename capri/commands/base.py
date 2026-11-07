"""Базовые классы, контекст и структуры данных командной системы."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class CommandResult:
    """Результат выполнения команды с сообщением и статусом успешности."""

    message: str | None = None
    success: bool = True


@dataclass
class CommandContext:
    """Контекст выполнения команд с доступом к действиям питомца и системы."""

    speak: Callable[[str], Any]
    trigger_glitches: Callable[[], str]
    toggle_voice: Callable[[], str]
    locate_mouse: Callable[[], str]
    set_pose: Callable[[str], None]
    get_config: Callable[[str, Any], Any]
    set_config: Callable[[str, Any], None]
    expect_reply: Callable[..., None] | None = None
    action_bridge: Any = None
    debug_info: Callable[[], dict[str, Any]] | None = None


class BaseCommand:
    """Абстрактный базовый класс для всех команд приложения."""

    name: str = ""
    description: str = ""
    aliases: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    takes_argument: bool = False
    requires_confirmation: bool = False
    confirmation_prompt: str = ""

    def get_confirmation_prompt(self) -> str:
        if self.confirmation_prompt:
            return self.confirmation_prompt
        desc = self.description.rstrip(". ")
        return f"Подтверди: «{self.name}» — {desc}. (да / нет)"

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        raise NotImplementedError
