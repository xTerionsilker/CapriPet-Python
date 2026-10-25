"""Блокировка экрана: штатное средство Windows 11 (аналог Win+L).

В Linux Capri подбирала команды окружения — ``loginctl``, ``qdbus`` с
 freedesktop ScreenSaver, ``xdg-screensaver`` и другие. В Windows блокировка
рабочего стола — это один экспорт ``user32.dll``: :func:`LockWorkStation`,
ровно тот же вызов, который выполняет сочетание `Win+L`. Прав
администратора не требуется, работает в любой сессии.

Модуль не зависит от Qt: окно только запускает :func:`run_lock` через
таймер, чтобы пользователь успел увидеть ответ. Интерфейс функций
совпадает с прежним подбором CLI-команд, поэтому ``capri.pet_window``
работает без изменений.

Использование::

    from capri.screen_lock import lock_commands, run_lock

    commands = lock_commands()
    if commands:
        run_lock(commands)
"""

from __future__ import annotations

import ctypes
import sys

#: Сколько секунд ждать команду блокировки (оставлено для совместимости API).
PER_COMMAND_TIMEOUT_S = 3

#: Экспорт ``user32.dll``, блокирующий рабочий стол (то же, что Win+L).
LOCK_EXPORT = "LockWorkStation"

#: Метка нативного вызова в списке «команд» — вместо пути к утилите.
LOCK_COMMAND = f"api:{LOCK_EXPORT}"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def _user32() -> ctypes.WinDLL | None:
    """Загрузить ``user32.dll`` и проверить наличие нужного экспорта."""
    if not is_windows():
        return None
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        getattr(user32, LOCK_EXPORT)
    except (AttributeError, OSError):
        return None
    return user32


def lock_commands() -> list[list[str]]:
    """Подобрать способы блокировки экрана текущего окружения.

    На Windows возвращается список из одной метки нативного вызова —
    интерфейс совпадает с подбором CLI-команд прежней версии. Вне Windows
    список пуст: Capri честно сообщает, что блокировка недоступна.
    """
    if _user32() is None:
        return []
    return [[LOCK_COMMAND]]


def run_lock(commands: list[list[str]]) -> bool:
    """Попробовать способы блокировки по очереди, пока один не сработает."""
    user32 = _user32()
    if user32 is None:
        return False
    for command in commands:
        if command and command[0] == LOCK_COMMAND:
            # LockWorkStation возвращает nonzero, когда запрос блокировки
            # поставлен в очередь; сама блокировка происходит сразу после.
            try:
                if user32.LockWorkStation():
                    return True
            except OSError:
                continue
    return False
