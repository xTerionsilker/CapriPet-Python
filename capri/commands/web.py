"""Web and media search command handlers for CapriPet."""

from __future__ import annotations

from ..integrations import web_search
from .base import BaseCommand, CommandContext


class GoogleSearchCommand(BaseCommand):
    """Найти запрос в Google."""

    name = "гугл"
    description = "найти запрос в Google."
    takes_argument = True
    aliases = (
        "загугли",
        "погугли",
        "гуглить",
        "искать в гугле",
        "найди в гугле",
        "поищи в гугле",
        "поискать в гугле",
        "поиск в гугле",
        "найди в интернете",
        "поищи в интернете",
    )
    keywords = (
        "гугл",
        "поиск",
        "интернет",
        "найди",
        "загугл",
        "погугл",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.search_google(query)
        return web_search.search_google(query)


class YouTubeSearchCommand(BaseCommand):
    """Найти запрос на YouTube."""

    name = "ютуб"
    description = "найти запрос на YouTube."
    takes_argument = True
    aliases = (
        "ютьюб",
        "искать на ютубе",
        "найди на ютубе",
        "найди в ютубе",
        "поищи на ютубе",
        "поищи в ютубе",
        "поискать на ютубе",
        "поиск на ютубе",
        "поиск в ютубе",
    )
    keywords = ("ютуб", "видео", "ролик", "ютюб")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        trimmed = query.strip()
        if not trimmed:
            return "Какое видео крутить? Скомандуй: «ютуб <запрос>»!"
        if ctx.action_bridge is not None:
            return ctx.action_bridge.search_youtube(trimmed)
        return web_search.search_youtube(trimmed)
