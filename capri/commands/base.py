from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CommandResult:
    """Результат выполнения команды."""
    message: str | None = None
    success: bool = True


@dataclass
class CommandContext:
    """Контекст для передачи окружения и колбэков в команды.
    
    Исключает прямую привязку к классу CapriWindow или циклическую зависимость.
    """
    speak: Callable[[str], Any]
    trigger_glitches: Callable[[], str]
    wild_glitch: Callable[[], str]
    toggle_voice: Callable[[], str]
    locate_mouse: Callable[[], str]
    set_pose: Callable[[str], None]
    get_config: Callable[[str, Any], Any]
    set_config: Callable[[str, Any], None]
    action_bridge: Any = None  # ActionBridge для фоновых асинхронных операций


class BaseCommand:
    """Базовый класс для всех команд питомца."""

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
        """Выполняет команду и возвращает текстовый ответ (или None)."""
        raise NotImplementedError
