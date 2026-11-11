"""Developer and diagnostic command handlers for CapriPet."""

from __future__ import annotations

from ..integrations import web_search
from .base import BaseCommand, CommandContext


def format_duration(seconds: float | None) -> str:
    """Форматирует длительность в секундах в человекочитаемый вид."""
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
    """Формирует текстовое описание текущего состояния модели Vosk."""
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
