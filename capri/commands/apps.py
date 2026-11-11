"""Application launch and process management command handlers for CapriPet."""

from __future__ import annotations

from .base import BaseCommand, CommandContext


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
