from __future__ import annotations

from .base import BaseCommand, CommandContext


class GlitchToggleCommand(BaseCommand):
    name = "глитч"
    description = "включить или выключить экранные глитчи."
    aliases = (
        "переключить глитч",
        "включить глитч",
        "выключить глитч",
        "глитчи",
        "глюки",
        "переключить глюки",
        "включить глюки",
        "выключить глюки",
        "эффекты",
        "переключить эффекты",
    )
    keywords = (
        "глитч",
        "глюк",
        "эффект",
        "цвет",
        "радуг",
        "визуал",
        "помех",
        "искажен",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        return ctx.trigger_glitches()


class LocateMouseCommand(BaseCommand):
    name = "где мышь"
    description = "указать на курсор мыши прицелом молний в реальном времени."
    aliases = (
        "где курсор",
        "найди мышь",
        "найди курсор",
        "поймай мышь",
        "поймай курсор",
        "потерял мышь",
        "потерял курсор",
        "потерял мышку",
        "верни мышь",
        "верни курсор",
        "где мышка",
        "найди мышку",
        "поймай мышку",
        "покажи мышь",
        "покажи мышку",
        "покажи курсор",
        "мышь",
        "курсор",
        "мышка",
    )
    keywords = ("мыш", "мышь", "мышка", "курсор", "пойма", "потеря", "покаж")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        return ctx.locate_mouse()
