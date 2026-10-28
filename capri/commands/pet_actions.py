from __future__ import annotations

from .base import BaseCommand, CommandContext


class ComplimentCommand(BaseCommand):
    name = "комплимент"
    description = "устроить дикие глитчи на 5 секунд."
    aliases = (
        "ты красивая",
        "капри ты красивая",
        "ты самая лучшая",
        "ты прекрасна",
        "комплимент капри",
        "ты охуенная",
        "ты ахуенная",
        "ты офигенная",
        "ты крутая",
        "ты классная",
        "ты супер",
        "ты огонь",
        "ты лучшая",
        "ты молодец",
        "ты милая",
        "ты красотка",
    )
    keywords = (
        "комплимент",
        "красив",
        "лучш",
        "прекрасн",
        "восторг",
        "охуен",
        "ахуен",
        "офиген",
        "афиген",
        "крут",
        "классн",
        "огонь",
        "потряс",
        "мил",
        "умниц",
        "молодец",
        "красот",
        "супер",
        "бомб",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        return ctx.wild_glitch()


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
