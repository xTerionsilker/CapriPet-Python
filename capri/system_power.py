"""Питание системы: выключение, спящий режим и перезагрузка (Windows 11).

Capri не реализует действия сама — она вызывает штатные средства Windows:
``shutdown.exe`` для выключения и перезагрузки и ``SetSuspendState`` из
``powrprof.dll`` для сна. Модуль не зависит от Qt: окно только запускает
:func:`run_power` через таймер, чтобы пользователь успел увидеть ответ.

Все действия выполняются с флагами ``/f`` (принудительно) и ``/t 0`` (без
отсчёта): пользователь уже подтвердил команду словами «да» в облачке, и
второго запроса быть не должно. Прав администратора эти команды не требуют.

Использование::

    from capri.system_power import power_commands, run_power

    commands = power_commands("poweroff")
    if commands:
        run_power(commands)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from shutil import which

#: Сколько секунд ждать одну команду питания.
PER_COMMAND_TIMEOUT_S = 5

#: Каталог системных утилит; на нетиповых установках берётся из окружения.
SYSTEM32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"

#: Действия и их кандидаты в порядке приоритета: shutdown.exe и его полный путь.
POWER_ACTIONS: dict[str, tuple[tuple[str, ...], ...]] = {
    "poweroff": (
        ("shutdown.exe", "/s", "/f", "/t", "0"),
        (str(SYSTEM32 / "shutdown.exe"), "/s", "/f", "/t", "0"),
    ),
    "suspend": (
        # У shutdown.exe прямого сна нет: SetSuspendState(bHibernate=F,
        # bForceCritical=T, bDisableWakeUp=T) — обычный спящий режим Win+X.
        ("rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"),
        (str(SYSTEM32 / "rundll32.exe"), "powrprof.dll,SetSuspendState", "0,1,0"),
    ),
    "reboot": (
        ("shutdown.exe", "/r", "/f", "/t", "0"),
        (str(SYSTEM32 / "shutdown.exe"), "/r", "/f", "/t", "0"),
    ),
}


def is_windows() -> bool:
    """Работает ли приложение под Windows — единственный поддерживаемый способ питания."""
    return sys.platform.startswith("win")


def power_commands(action: str) -> list[list[str]]:
    """Подобрать системные команды для ``action`` текущего окружения.

    ``action`` — ключ :data:`POWER_ACTIONS`: ``"poweroff"``, ``"suspend"``
    или ``"reboot"``. Вне Windows список пуст: Capri честно сообщает, что
    действие недоступно. Недоступные утилиты отбрасываются сразу.
    """
    if not is_windows():
        return []
    commands: list[list[str]] = []
    for candidate in POWER_ACTIONS[action]:
        program, *arguments = candidate
        resolved = _resolve(program)
        if resolved is not None:
            commands.append([resolved, *arguments])
    return commands


def _resolve(program: str) -> str | None:
    """Найти утилиту в PATH, а затем прямо в ``%SystemRoot%\\System32``."""
    if "\\" in program or "/" in program:
        return program if Path(program).is_file() else None
    found = which(program)
    if found:
        return found
    fallback = SYSTEM32 / program
    return str(fallback) if fallback.is_file() else None


def run_power(commands: list[list[str]]) -> bool:
    """Попробовать команды по очереди, пока одна не сработает."""
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=PER_COMMAND_TIMEOUT_S,
                # При запуске через pythonw.exe консольное окно мелькать не должно.
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            # Выключение и перезагрузка могут оборвать процесс —
            # считаем это успехом.
            return True
        except OSError:
            continue
        if result.returncode == 0:
            return True
    return False
