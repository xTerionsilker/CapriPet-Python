from __future__ import annotations

from .base import BaseCommand, CommandContext
from ..integrations import ollama


class OllamaAskCommand(BaseCommand):
    name = "слушай"
    description = "спросить локальную модель Ollama."
    takes_argument = True
    aliases = (
        "спроси модель",
        "спроси локально",
        "локальная модель",
        "нейросеть",
        "нейронка",
        "спроси нейросеть",
        "спроси нейронку",
        "спроси у модели",
        "ии",
        "спроси ии",
        "ollama",
        "оллама",
        "qwen",
        "квен",
        "квэн",
    )
    keywords = (
        "слушай",
        "ollama",
        "оллам",
        "qwen",
        "квен",
        "квэн",
        "нейросет",
        "нейронк",
        "ии",
        "модел",
        "спроси",
        "спросить",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.ask_ollama(query)
        # Синхронный fallback
        prompt = query.strip()
        if not prompt:
            return "Что спросить у локальной модели?"
        try:
            return ollama.ask(prompt)
        except Exception:
            return "Локальная модель не ответила."
