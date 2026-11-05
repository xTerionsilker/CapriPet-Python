from __future__ import annotations

from typing import Any
import webbrowser

from .base import BaseCommand, CommandContext
from ..integrations import spotify, web_search
from ..integrations.system_control import (
    lock_commands,
    power_commands,
    run_lock,
    run_power,
)


def format_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "неизвестно"
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours} ч {minutes:02d} мин"
    if minutes:
        return f"{minutes} мин {secs:02d} с"
    return f"{secs} с"


def _describe_vosk(info: dict[str, object]) -> str:
    if not info.get("available", False):
        return "недоступна (библиотека vosk не установлена)"
    model_name = str(info.get("model_name") or "")
    model_version = str(info.get("model_version") or "")
    vosk_version = str(info.get("vosk_version") or "")
    details: list[str] = []
    if model_name:
        details.append(model_name)
    if model_version:
        details.append(f"модель {model_version}")
    if vosk_version:
        details.append(f"vosk {vosk_version}")
    suffix = f" ({', '.join(details)})" if details else ""
    if info.get("initialized", False):
        return f"инициализирована{suffix}"
    if info.get("loading", False):
        return f"загружается в фоне{suffix}"
    if model_name:
        return f"не загружена, загрузится при первом распознавании{suffix}"
    return "не инициализирована, локальная модель не найдена"


class DebugCommand(BaseCommand):
    name = "дебаг"
    description = "показать состояние системы: модель Vosk, таймер напоминаний и время работы."
    aliases = (
        "диагностика",
        "самодиагностика",
        "отладка",
        "статус",
        "статус системы",
        "состояние",
        "состояние системы",
        "инфо",
        "информация",
        "проверка системы",
    )
    keywords = (
        "дебаг",
        "диагност",
        "отлад",
        "статус",
        "состояни",
        "информац",
        "проверк",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.debug_info is None:
            return "Диагностика недоступна."
        try:
            info = ctx.debug_info()
        except Exception:
            return "Не удалось собрать диагностику."

        vosk = info.get("vosk") or {}
        vosk_text = _describe_vosk(vosk if isinstance(vosk, dict) else {})
        reminder_text = format_duration(info.get("next_reminder_seconds"))
        uptime_text = format_duration(info.get("uptime_seconds"))

        return (
            f"Модель Vosk: {vosk_text}\n"
            f"Напомню о себе через: {reminder_text}\n"
            f"Время работы: {uptime_text}"
        )


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
            return "Что искать на YouTube? Скажи: «ютуб <запрос>»."
        if ctx.action_bridge is not None:
            return ctx.action_bridge.search_youtube(trimmed)
        return web_search.search_youtube(trimmed)


class UpdateCommand(BaseCommand):
    name = "обновление"
    description = "проверить обновления CapriPet на GitHub."
    aliases = (
        "обновления",
        "обновить",
        "обновись",
        "проверить обновления",
        "проверь обновления",
        "проверить обновление",
        "проверь обновление",
        "апдейт",
        "чекни обновления",
        "страница обновления",
        "репозиторий",
        "гитхаб",
    )
    keywords = (
        "обновление",
        "обновления",
        "обновить",
        "обнови",
        "апдейт",
        "гитхаб",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None and hasattr(ctx.action_bridge, "check_updates"):
            return ctx.action_bridge.check_updates()
        if ctx.action_bridge is not None and hasattr(ctx.action_bridge, "open_update_page"):
            return ctx.action_bridge.open_update_page()
        return web_search.open_update_page()


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
        return "Действие недоступно: ActionBridge не инициализирован."


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


class SpotifyCurrentTrackCommand(BaseCommand):
    name = "что играет"
    description = "узнать, какой трек сейчас играет в Spotify."
    aliases = (
        "что сейчас играет",
        "какой трек играет",
        "какая песня играет",
        "что за трек",
        "что за песня",
        "название трека",
        "название песни",
        "текущий трек",
        "текущая песня",
        "кто поет",
        "кто поёт",
        "че играет",
        "че за трек",
        "че за песня",
        "какой трек",
        "какая песня",
    )
    keywords = ("играет", "трек", "песн", "поет", "поёт", "назван")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.spotify_current_track()
        return spotify.current_track()


class LockScreenCommand(BaseCommand):
    name = "блокировка"
    description = "заблокировать экран (аналог Super+L)."
    requires_confirmation = True
    aliases = (
        "заблокировать",
        "заблокируй",
        "блокировать",
        "заблокировать экран",
        "заблокируй экран",
        "экран блокировки",
        "блокировка экрана",
        "лок",
        "лок скрин",
        "залочь",
        "залочить",
        "залочь экран",
        "залочить экран",
        "выключи экран",
        "погаси экран",
        "супер л",
        "заблок",
        "я отойду",
        "отойду",
    )
    keywords = ("блокир", "заблок", "экран", "лок", "залоч")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.lock_screen()
        commands = lock_commands()
        if not commands or not run_lock(commands):
            return "Не удалось заблокировать экран."
        return "Блокирую экран."


class PowerOffCommand(BaseCommand):
    name = "выключи"
    description = "выключить компьютер."
    requires_confirmation = True
    aliases = (
        "я спать",
        "выключи пк",
        "выключить пк",
        "выключи компьютер",
        "выключить компьютер",
        "выруби пк",
        "выруби компьютер",
        "выключись",
        "спокойной ночи",
        "шатдаун",
        "паверофф",
        "поверофф",
        "выключение пк",
        "выключить",
    )
    keywords = (
        "выключ",
        "спат",
        "спят",
        "шатдаун",
        "паверофф",
        "поверофф",
        "питан",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.power_off()
        commands = power_commands("poweroff")
        if not commands or not run_power(commands):
            return "Не удалось выключить компьютер."
        return "Выключаю ПК."


class SuspendCommand(BaseCommand):
    name = "сон"
    description = "перевести компьютер в спящий режим."
    requires_confirmation = True
    aliases = (
        "я гулять",
        "спящий режим",
        "перевести в спящий режим",
        "переведи в спящий режим",
        "режим сна",
        "усни",
        "уснуть",
        "замри",
        "отдохни",
        "передохни",
        "приостанови компьютер",
        "слип",
        "суспенд",
    )
    keywords = (
        "спящ",
        "сон",
        "усн",
        "слип",
        "суспенд",
        "замр",
        "гуля",
        "отдохн",
        "передохн",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.suspend()
        commands = power_commands("suspend")
        if not commands or not run_power(commands):
            return "Не удалось перевести компьютер в спящий режим."
        return "Ухожу в спящий режим."


class RebootCommand(BaseCommand):
    name = "перезагрузка"
    description = "перезагрузить компьютер."
    requires_confirmation = True
    aliases = (
        "перезагрузи",
        "перезагрузить",
        "перезагрузи пк",
        "перезагрузить пк",
        "перезагрузка пк",
        "перезагрузка компьютера",
        "перезагрузись",
        "ребутнись",
        "рестартнись",
        "ребутни комп",
        "выключить и включить",
        "перезагрузи компьютер",
        "перезагрузить компьютер",
        "рестарт",
        "ребут",
        "ребутни",
        "рестартни",
    )
    keywords = ("перезагруз", "рестарт", "ребут")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.reboot()
        commands = power_commands("reboot")
        if not commands or not run_power(commands):
            return "Не удалось перезагрузить компьютер."
        return "Перезагружаю ПК."


class LaunchAppCommand(BaseCommand):
    name = "запусти"
    description = "найти и запустить установленное приложение."
    takes_argument = True
    aliases = (
        "запусти приложение",
        "запустить",
        "запустить приложение",
        "открой",
        "открыть",
        "открой приложение",
        "открыть приложение",
        "включи приложение",
        "включить приложение",
        "старт",
        "стартуй",
    )
    keywords = ("запусти", "запустить", "открой", "открыть", "старт", "приложение", "программу")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        trimmed = query.strip()
        if not trimmed:
            return "Какое приложение запустить? Скажи: «запусти <название>»."
        if ctx.action_bridge is not None:
            return ctx.action_bridge.launch_app(trimmed)
        return f"Ищу приложение: {trimmed}"


class KillAppCommand(BaseCommand):
    name = "убей"
    description = "найти и завершить запущенный процесс или приложение."
    takes_argument = True
    aliases = (
        "убей процесс",
        "убей приложение",
        "убить",
        "убить процесс",
        "убить приложение",
        "закрой",
        "закрыть",
        "закрой процесс",
        "закрыть процесс",
        "закрой приложение",
        "закрыть приложение",
        "заверши",
        "завершить",
        "заверши процесс",
        "завершить процесс",
        "прибей",
        "прибить",
        "стоп процесс",
    )
    keywords = ("убей", "убить", "закрой", "закрыть", "заверши", "завершить", "прибей", "прибить", "процесс")

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        trimmed = query.strip()
        if not trimmed:
            return "Какой процесс убить? Скажи: «убей <название>»."
        if ctx.action_bridge is not None:
            return ctx.action_bridge.kill_app(trimmed)
        return f"Ищу процессы: {trimmed}"
