from __future__ import annotations

from .base import BaseCommand, CommandContext


class AskAICommand(BaseCommand):
    name = "слушай"
    description = "спросить нейросеть через API (настройки в ai_config.json)."
    takes_argument = True
    aliases = (
        "спроси модель",
        "нейросеть",
        "нейронка",
        "спроси нейросеть",
        "спроси нейронку",
        "спроси у модели",
        "ии",
        "спроси ии",
        "спроси ai",
        "ai",
        "аи",
        "модель",
    )
    keywords = (
        "слушай",
        "нейросет",
        "нейронк",
        "ии",
        "модел",
        "спроси",
        "спросить",
        "ai",
        "аи",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.ask_ai(query)
        return "Действие недоступно: ActionBridge не инициализирован."
