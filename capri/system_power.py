"""Питание системы: выключение, спящий режим и перезагрузка.

Capri не реализует действия сама — она вызывает штатные средства
окружения и пробует их по очереди, пока какая-нибудь не сработает.
Модуль не зависит от Qt: окно только запускает :func:`run_power` через
таймер, чтобы пользователь успел увидеть ответ.

Использование::

    from capri.system_power import power_commands, run_power

    commands = power_commands("poweroff")
    if commands:
        run_power(commands)
"""

from __future__ import annotations

import shutil
import subprocess

#: Сколько секунд ждать одну команду питания.
PER_COMMAND_TIMEOUT_S = 5

#: Действия и их кандидаты в порядке приоритета: systemd, logind, утилиты.
POWER_ACTIONS: dict[str, tuple[tuple[str, ...], ...]] = {
    "poweroff": (
        ("systemctl", "poweroff"),
        ("loginctl", "poweroff"),
        ("shutdown", "-h", "now"),
        ("poweroff",),
    ),
    "suspend": (
        ("systemctl", "suspend"),
        ("loginctl", "suspend"),
        ("pm-suspend",),
    ),
    "reboot": (
        ("systemctl", "reboot"),
        ("loginctl", "reboot"),
        ("shutdown", "-r", "now"),
        ("reboot",),
    ),
}


def power_commands(action: str) -> list[list[str]]:
    """Подобрать системные команды для ``action`` текущего окружения.

    ``action`` — ключ :data:`POWER_ACTIONS`: ``"poweroff"``, ``"suspend"``
    или ``"reboot"``. Недоступные утилиты отбрасываются сразу.
    """
    candidates = POWER_ACTIONS[action]
    return [
        list(command)
        for command in candidates
        if shutil.which(command[0])
    ]


def run_power(commands: list[list[str]]) -> bool:
    """Попробовать команды по очереди, пока одна не сработает."""
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=PER_COMMAND_TIMEOUT_S,
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
