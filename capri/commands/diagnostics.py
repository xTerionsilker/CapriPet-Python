from __future__ import annotations

from .base import BaseCommand, CommandContext


def format_duration(seconds: int | float | None) -> str:
    """Форматирует длительность в человекочитаемый вид."""
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
