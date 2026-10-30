from __future__ import annotations

from .base import BaseCommand, CommandContext
from ..integrations import spotify


class SpotifyPlayCommand(BaseCommand):
    name = "спотифай"
    description = "найти и включить музыку в Spotify."
    takes_argument = True
    aliases = (
        "спотик",
        "включи музыку",
        "поставь музыку",
        "включи спотифай",
        "включи в спотифае",
        "найди музыку",
        "найди песню",
        "включи песню",
        "поставь песню",
    )
    keywords = (
        "музык",
        "песн",
        "трек",
        "спотиф",
        "плейлист",
        "альбом",
        "исполнител",
        "мелоди",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.spotify_play(query)
        # Fallback при прямом вызове без ActionBridge
        query = query.strip()
        if not query:
            return "Что включить? Скажи: «спотифай <запрос>»."
        return spotify.play(query)


class SpotifyPauseCommand(BaseCommand):
    name = "пауза"
    description = "поставить музыку в Spotify на паузу."
    aliases = (
        "поставь на паузу",
        "паузу",
        "приостанови музыку",
        "приостанови",
        "стоп",
        "останови",
        "останови музыку",
        "заткнись",
        "замолчи",
        "помолчи",
        "тихо",
        "стоп музыка",
    )
    keywords = ("пауз", "останов", "стоп", "тихо", "приглуш", "заткн", "замолч")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.spotify_pause()
        return spotify.pause()


class SpotifyResumeCommand(BaseCommand):
    name = "продолжить"
    description = "продолжить воспроизведение в Spotify."
    aliases = (
        "плей",
        "играй",
        "продолжи",
        "продолжи музыку",
        "продолжай",
        "продолжай играть",
        "играй дальше",
        "возобнови",
        "возобнови музыку",
    )
    keywords = ("продолж", "играй", "возобнов", "плей", "громче")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.spotify_resume()
        return spotify.resume()


class SpotifyNextCommand(BaseCommand):
    name = "следующий трек"
    description = "включить следующий трек в Spotify."
    aliases = (
        "следующий",
        "след",
        "некст",
        "некст трек",
        "скип",
        "скипни",
        "скип трек",
        "скипни трек",
        "пропусти",
        "пропусти трек",
        "другой трек",
        "включи другой трек",
        "переключи трек",
        "следующая песня",
        "следующая",
        "дальше",
        "переключи",
    )
    keywords = ("следующ", "дальше", "переключ", "некст", "скип", "пропуст")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.spotify_next()
        return spotify.next_track()


class SpotifyPreviousCommand(BaseCommand):
    name = "предыдущий трек"
    description = "вернуться к предыдущему треку в Spotify."
    aliases = (
        "предыдущий",
        "прев",
        "превиус",
        "назад",
        "трек назад",
        "прошлый трек",
        "прошлая песня",
        "прошлый",
        "верни трек",
        "предыдущая песня",
        "предыдущая",
    )
    keywords = ("предыдущ", "назад", "прев", "превиус", "верни", "прошл")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.spotify_previous()
        return spotify.previous_track()
