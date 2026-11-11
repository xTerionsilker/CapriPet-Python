"""System audio volume control command handlers for CapriPet."""

from __future__ import annotations

import re

from ..core.morphology import normalize_spoken_numbers
from .base import BaseCommand, CommandContext


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
