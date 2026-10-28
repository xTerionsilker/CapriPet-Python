from __future__ import annotations

from .base import BaseCommand, CommandContext
from ..integrations import web_search


class GoogleSearchCommand(BaseCommand):
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
        "google",
        "искать в google",
        "найди в google",
        "поищи в google",
        "поиск в google",
        "найди в интернете",
        "поищи в интернете",
    )
    keywords = (
        "гугл",
        "google",
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
    name = "ютуб"
    description = "найти запрос на YouTube."
    takes_argument = True
    aliases = (
        "ютьюб",
        "youtube",
        "искать на ютубе",
        "найди на ютубе",
        "найди в ютубе",
        "поищи на ютубе",
        "поищи в ютубе",
        "поискать на ютубе",
        "поиск на ютубе",
        "поиск в ютубе",
        "искать на youtube",
        "найди на youtube",
        "поищи на youtube",
        "поиск на youtube",
    )
    keywords = ("ютуб", "youtube", "видео", "ролик", "ютюб")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.search_youtube(query)
        return web_search.search_youtube(query)
