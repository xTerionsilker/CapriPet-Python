"""Блокировка экрана: подбор и запуск системных команд.

Capri не реализует блокировку сама — она вызывает штатные средства
окружения и пробует их по очереди, пока какая-нибудь не сработает.
Модуль не зависит от Qt: окно только запускает :func:`run_lock` через
таймер, чтобы пользователь успел увидеть ответ.

Использование::

    from capri.screen_lock import lock_commands, run_lock

    commands = lock_commands()
    if commands:
        run_lock(commands)
"""

from __future__ import annotations

import os
import shutil
import subprocess

#: Сколько секунд ждать одну команду блокировки.
PER_COMMAND_TIMEOUT_S = 3


def lock_commands() -> list[list[str]]:
    """Подобрать команды блокировки экрана текущего окружения."""
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    candidates: list[list[str]] = []

    if any(name in desktop for name in ("KDE", "PLASMA")):
        qdbus = (
            "qdbus6"
            if shutil.which("qdbus6")
            else "qdbus"
            if shutil.which("qdbus")
            else None
        )
        if qdbus:
            candidates.append(
                [
                    qdbus,
                    "org.freedesktop.ScreenSaver",
                    "/ScreenSaver",
                    "Lock",
                ]
            )

    # Универсальный способ через systemd-logind; без ID блокируется
    # сессия вызывающего процесса. Это аналог Super+L.
    candidates.append(["loginctl", "lock-session"])
    candidates.append(["xdg-screensaver", "lock"])
    candidates.append(["gnome-screensaver-command", "-l"])
    candidates.append(["cinnamon-screensaver-command", "-l"])
    candidates.append(["xfce4-screensaver-command", "-l"])
    candidates.append(["light-locker-command", "-l"])

    return [command for command in candidates if shutil.which(command[0])]


def run_lock(commands: list[list[str]]) -> bool:
    """Попробовать команды блокировки по очереди, пока одна не сработает."""
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=PER_COMMAND_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            # Блокировщик может работать до разблокировки — считаем успехом.
            return True
        except OSError:
            continue
        if result.returncode == 0:
            return True
    return False
