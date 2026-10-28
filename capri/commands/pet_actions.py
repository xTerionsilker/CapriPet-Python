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


class VoiceToggleCommand(BaseCommand):
    name = "голос"
    description = "начать или остановить голосовой ввод."
    aliases = (
        "микрофон",
        "слушать",
        "говорить",
        "голосовой ввод",
        "запись",
        "включить голос",
        "выключить голос",
        "включить микрофон",
        "выключить микрофон",
    )
    keywords = ("голос", "микрофон", "слуша", "говори", "запис")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        return ctx.toggle_voice()


class LocateMouseCommand(BaseCommand):
    name = "где мышь"
    description = "появиться на курсоре мыши и телепортировать его вместе с собой в центр экрана."
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
        "мышь",
        "курсор",
        "мышка",
    )
    keywords = ("мыш", "мышь", "мышка", "курсор", "пойма", "потеря")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        return ctx.locate_mouse()
