from __future__ import annotations

from .base import BaseCommand, CommandContext
from ..integrations.screen_lock import lock_commands, run_lock
from ..integrations.system_power import power_commands, run_power


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
    name = "я спать"
    description = "выключить компьютер."
    requires_confirmation = True
    aliases = (
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
        "спат",
        "спят",
        "выключ",
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
    name = "я гулять"
    description = "перевести компьютер в спящий режим."
    requires_confirmation = True
    aliases = (
        "спящий режим",
        "перевести в спящий режим",
        "переведи в спящий режим",
        "режим сна",
        "усни",
        "уснуть",
        "сон",
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

