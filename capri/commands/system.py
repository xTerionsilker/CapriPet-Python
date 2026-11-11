"""System lifecycle, security, maintenance and registry command handlers for CapriPet."""

from __future__ import annotations

from ..integrations import registry_scanner, system_cleaner
from ..integrations.system_control import (
    lock_commands,
    power_commands,
    run_lock,
    run_power,
)
from .base import BaseCommand, CommandContext


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
        return (
            f"Шреддер сработал на ура: растёрла {res.files_deleted} кусков мусора, "
            f"освободила тебе целых {freed_str}!"
        )


class RegistryCommand(BaseCommand):
    """Сканирование реестра Windows на пустые и битые ветки с открытием отчёта."""

    name = "реестр"
    description = "сканировать реестр Windows на пустые и битые ключи с сохранением отчёта."
    aliases = (
        "сканировать реестр",
        "сканируй реестр",
        "проверить реестр",
        "проверь реестр",
        "анализ реестра",
        "проверка реестра",
        "битые ключи",
        "почистить реестр",
        "почисти реестр",
        "очистка реестра",
        "очисти реестр",
        "чек реестра",
        "registry",
        "scan registry",
        "check registry",
        "clean registry",
    )
    keywords = (
        "реестр",
        "регистр",
        "registry",
    )

    def execute(self, ctx: CommandContext, query: str = "") -> str | None:
        if ctx.action_bridge is not None:
            return ctx.action_bridge.scan_registry()
        report = registry_scanner.perform_registry_scan(open_report=True)
        if not report.issues:
            return (
                f"Прошерстила {report.total_scanned} записей реестра: всё чисто, "
                "ни единого заброшенного ключа!"
            )
        return (
            f"Анализ реестра завершён: откопала {len(report.issues)} аномалий! "
            "Текстовый отчёт уже открыт."
        )
