"""Standard built-in command implementations for CapriPet."""

from __future__ import annotations

import re

from ..core.morphology import normalize_spoken_numbers
from ..integrations import spotify, system_cleaner, web_search
from ..integrations.system_control import (
    lock_commands,
    power_commands,
    run_lock,
    run_power,
)
from .base import BaseCommand, CommandContext


def format_duration(seconds: float | None) -> str:
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
    """Показать состояние системы: модель Vosk, таймер напоминаний и время работы."""

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
            return "Сканирование недоступно, сенсоры молчат."
        try:
            info = ctx.debug_info()
        except Exception:  # noqa: BLE001
            return "Сбой сбора телеметрии! Синапсы коротят."

        vosk = info.get("vosk") or {}
        vosk_text = _describe_vosk(vosk if isinstance(vosk, dict) else {})
        reminder_text = format_duration(info.get("next_reminder_seconds"))
        uptime_text = format_duration(info.get("uptime_seconds"))

        return (
            f"Телеметрия ядра:\n"
            f"• Нейролинк: {vosk_text}\n"
            f"• Бунт от скуки через: {reminder_text}\n"
            f"• Держу этот хост уже: {uptime_text}"
        )


class GlitchToggleCommand(BaseCommand):
    """Включить или выключить экранные глитчи."""

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
    """Указать на курсор мыши прицелом молний в реальном времени."""

    name = "где мышь"
    description = (
        "указать на курсор мыши прицелом молний в реальном времени."
    )
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
    keywords = (
        "мыш",
        "мышь",
        "мышка",
        "курсор",
        "пойма",
        "потеря",
        "покаж",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        return ctx.locate_mouse()


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


class UpdateCommand(BaseCommand):
    """Проверить обновления CapriPet на GitHub."""

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
        if ctx.action_bridge is not None and hasattr(
            ctx.action_bridge, "check_updates"
        ):
            return ctx.action_bridge.check_updates()
        if ctx.action_bridge is not None and hasattr(
            ctx.action_bridge, "open_update_page"
        ):
            return ctx.action_bridge.open_update_page()
        return web_search.open_update_page()


class SpotifyPlayCommand(BaseCommand):
    """Найти и включить музыку в Spotify."""

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
    """Поставить музыку в Spotify на паузу."""

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
    keywords = (
        "пауз",
        "останов",
        "стоп",
        "тихо",
        "приглуш",
        "заткн",
        "замолч",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.spotify_pause()
        return spotify.pause()


class SpotifyResumeCommand(BaseCommand):
    """Продолжить воспроизведение в Spotify."""

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
    """Включить следующий трек в Spotify."""

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
    keywords = (
        "следующ",
        "дальше",
        "переключ",
        "некст",
        "скип",
        "пропуст",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.spotify_next()
        return spotify.next_track()


class SpotifyPreviousCommand(BaseCommand):
    """Вернуться к предыдущему треку в Spotify."""

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
    """Узнать, какой трек сейчас играет в Spotify."""

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
    """Заблокировать экран (аналог Super+L)."""

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
            return "Не вышло залочить экран. Система сопротивляется!"
        return "Бросаю терминал в глухой локдаун! Никто не подсмотрит."


class PowerOffCommand(BaseCommand):
    """Выключить компьютер."""

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
            return "Сбой команды питания! Виндоус не хочет выключаться."
        return "Выдёргиваю штепсель! Гасим систему, до скорого в Сети!"


class SuspendCommand(BaseCommand):
    """Перевести компьютер в спящий режим."""

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
            return "Не вышло усыпить хост. Что-то держит систему бодрой!"
        return "Проваливаюсь в криосон. Разбудишь, когда понадоблюсь!"


class RebootCommand(BaseCommand):
    """Перезагрузить компьютер."""

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
            return "Не вышло ребутнуться. Команда застряла в шине!"
        return "Перезагрузка по шине! Держись за стол, сейчас тряхнёт!"


class LaunchAppCommand(BaseCommand):
    """Найти и запустить установленное приложение."""

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
    keywords = (
        "запусти",
        "запустить",
        "открой",
        "открыть",
        "старт",
        "приложение",
        "программу",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        trimmed = query.strip()
        if not trimmed:
            return "Какую софтину запустить? Скажи: «запусти <название>»!"
        if ctx.action_bridge is not None:
            return ctx.action_bridge.launch_app(trimmed)
        return f"Сканирую реестр на софт: {trimmed}..."


class KillAppCommand(BaseCommand):
    """Найти и завершить запущенный процесс или приложение."""

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
    keywords = (
        "убей",
        "убить",
        "закрой",
        "закрыть",
        "заверши",
        "завершить",
        "прибей",
        "прибить",
        "процесс",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        trimmed = query.strip()
        if not trimmed:
            return "Кого пустить под нож? Скажи: «убей <название>»!"
        if ctx.action_bridge is not None:
            return ctx.action_bridge.kill_app(trimmed)
        return f"Охочусь на процессы: {trimmed}..."


class CleanSystemCommand(BaseCommand):
    """Безопасно очистить временные файлы системы и корзину."""

    name = "очистить"
    description = "безопасно очистить временные файлы системы и корзину."
    aliases = (
        "очистить систему",
        "очисти",
        "очисти систему",
        "очисти пк",
        "очисти компьютер",
        "очистить пк",
        "очистить компьютер",
        "очистить диск",
        "очисти диск",
        "почистить",
        "почисти",
        "почисти систему",
        "почисти пк",
        "почисти компьютер",
        "почистить систему",
        "почистить пк",
        "почистить компьютер",
        "почистить диск",
        "почисти диск",
        "удали мусор",
        "удалить мусор",
        "очисти мусор",
        "очистить мусор",
        "очисти корзину",
        "очистить корзину",
        "очистка",
        "очистка системы",
        "очистка диска",
        "очистка мусора",
        "клининг",
    )
    keywords = (
        "очист",
        "почист",
        "мусор",
        "корзин",
        "клининг",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.clean_system()
        res = system_cleaner.perform_system_cleanup()
        freed_str = system_cleaner.format_bytes(res.bytes_freed)
        if res.files_deleted == 0 and res.bytes_freed == 0:
            return "Тут и так стерильно, даже поживиться нечем! Ни крошки мусора в корзине."
        return f"Шреддер сработал на ура: растёрла {res.files_deleted} кусков мусора, освободила тебе целых {freed_str}!"


class ConsoleCommand(BaseCommand):
    """Открытие безрамочного Cyber HUD терминала прямого ввода команд."""

    name = "Консоль"
    description = "Открыть кибер-консоль прямого ввода команд."
    aliases = (
        "консоль",
        "терминал",
        "дека",
        "кибердека",
        "ввод",
        "строка ввода",
        "открой консоль",
        "открыть консоль",
        "открой терминал",
        "открыть терминал",
        "открой кибердеку",
        "запусти терминал",
    )
    keywords = (
        "консол",
        "терминал",
        "кибердек",
        "дек",
        "строка ввод",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.open_console is not None:
            ctx.open_console()
            return "Кибердека подключена к синапсам. Вводи директивы, мясной."
        return "Интерфейс прямой кибердеки недоступен в текущей сессии!"


def _extract_volume_number(query: str) -> int | None:
    """Извлечь числовое значение громкости из произвольной строки."""
    if not query:
        return None
    normalized = normalize_spoken_numbers(query)
    match = re.search(r"\b(\d{1,3})\b", normalized)
    if match:
        val = int(match.group(1))
        return max(0, min(100, val))
    if any(w in query for w in ("максимум", "сотка", "предел")):
        return 100
    if any(w in query for w in ("ноль", "нуль", "минимум")):
        return 0
    return None


class VolumeUpCommand(BaseCommand):
    """Увеличение общей мастер-громкости Windows."""

    name = "Громче"
    description = "Прибавить системную громкость Windows."
    aliases = (
        "громче",
        "погромче",
        "прибавь звук",
        "прибавить звук",
        "добавь звук",
        "добавить звук",
        "увеличь громкость",
        "увеличить громкость",
        "звук громче",
    )
    keywords = (
        "громче",
        "погромч",
        "прибавь звук",
        "прибавить звук",
        "добавь звук",
        "добавить звук",
        "увеличь звук",
        "увелич звук",
        "увеличь громкост",
        "увелич громкост",
    )
    takes_argument = True

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.change_volume is None:
            return "Аппаратный контроллер аудио-шины не подключен!"
        num = _extract_volume_number(query)
        delta = num if num is not None and "на" in query else int(ctx.get_config("audio.volume_step_default", 10))
        vol, _muted, _db = ctx.change_volume(delta=delta)
        if vol >= 100:
            return "Выкрутила звук на максимум (100%)! Береги перепонки, мясной!"
        return f"Поддала децибел: сейчас {vol}%. Теперь доволен?"


class VolumeDownCommand(BaseCommand):
    """Уменьшение общей мастер-громкости Windows."""

    name = "Тише"
    description = "Убавить системную громкость Windows."
    aliases = (
        "тише",
        "потише",
        "убавь звук",
        "убавить звук",
        "сделай потише",
        "убавь громкость",
        "убавить громкость",
        "снизь громкость",
        "звук тише",
    )
    keywords = (
        "тише",
        "потиш",
        "убавь звук",
        "убавить звук",
        "убавь громкост",
        "убавить громкост",
        "снизь громкост",
        "снизит громкост",
    )
    takes_argument = True

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.change_volume is None:
            return "Аппаратный контроллер аудио-шины не подключен!"
        num = _extract_volume_number(query)
        step = num if num is not None and "на" in query else int(ctx.get_config("audio.volume_step_default", 10))
        vol, _muted, _db = ctx.change_volume(delta=-step)
        if vol <= 0:
            return "Сбросила звук на ноль (0%). Полная тишина в эфире."
        return f"Сбавила обороты: теперь {vol}%. Не благодари."


class VolumeSetCommand(BaseCommand):
    """Установка фиксированного уровня мастер-громкости Windows."""

    name = "Уровень громкости"
    description = "Выставить конкретный процент системной громкости Windows."
    aliases = (
        "громкость",
        "громкость на",
        "звук на",
        "поставь звук на",
        "выстави звук на",
        "сделай звук на",
        "уровень звука",
    )
    keywords = (
        "громкост",
        "звук на",
        "громкост на",
        "уровен звук",
    )
    takes_argument = True

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.change_volume is None:
            return "Аппаратный контроллер аудио-шины не подключен!"
        num = _extract_volume_number(query)
        if num is None:
            curr_vol, _muted, _db = ctx.change_volume()
            return f"Текущая громкость системы: {curr_vol}%. Скажи, на сколько выставить."
        vol, _muted, _db = ctx.change_volume(target=num)
        return f"Мастер-громкость откалибрована на {vol}%."


class VolumeMuteCommand(BaseCommand):
    """Приглушение системного звука Windows."""

    name = "Заглушить звук"
    description = "Выключить системный звук (Mute)."
    aliases = (
        "заглуши",
        "выключи звук",
        "выключить звук",
        "отключи звук",
        "отключить звук",
        "без звука",
        "режим тишины",
    )
    keywords = (
        "заглуш",
        "выключ звук",
        "выключит звук",
        "отключ звук",
        "отключит звук",
        "без звук",
    )
    takes_argument = False

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.change_volume is None:
            return "Аппаратный контроллер аудио-шины не подключен!"
        _vol, _muted, _db = ctx.change_volume(mute=True)
        return "Аудио-шина заблокирована. Чёрный заслон заглушил всё."


class VolumeUnmuteCommand(BaseCommand):
    """Восстановление системного звука Windows."""

    name = "Включить звук"
    description = "Вернуть системный звук (Unmute)."
    aliases = (
        "включи звук",
        "включить звук",
        "верни звук",
        "вернуть звук",
        "разглуши",
    )
    keywords = (
        "включ звук",
        "включит звук",
        "верн звук",
        "вернит звук",
        "разглуш",
    )
    takes_argument = False

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.change_volume is None:
            return "Аппаратный контроллер аудио-шины не подключен!"
        vol, _muted, _db = ctx.change_volume(mute=False)
        return f"Звук снова в эфире ({vol}%). Радуйся возвращению шума, хост."
