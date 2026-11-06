from __future__ import annotations

import ctypes
from ctypes import wintypes
import shutil
import subprocess

from PySide6.QtCore import QPoint
from PySide6.QtGui import QCursor

PER_COMMAND_TIMEOUT_S = 5

POWER_ACTIONS: dict[str, tuple[tuple[str, ...], ...]] = {
    "poweroff": (
        ("shutdown", "/s", "/t", "0"),
    ),
    "suspend": (
        ("rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"),
    ),
    "reboot": (
        ("shutdown", "/r", "/t", "0"),
    ),
}


class _POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


def get_mouse_position() -> QPoint:
    try:
        pt = _POINT()
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            return QPoint(pt.x, pt.y)
    except Exception:
        pass
    return QCursor.pos()


def move_mouse_to(
    x: int, y: int, screen_index: int | None = None
) -> bool:
    try:
        if ctypes.windll.user32.SetCursorPos(int(x), int(y)):
            return True
    except Exception:
        pass
    try:
        QCursor.setPos(x, y)
        return True
    except Exception:
        return False


def move_mouse_to_center(
    screen_center: QPoint | None = None, screen_index: int | None = None
) -> bool:
    if screen_center is not None:
        return move_mouse_to(
            screen_center.x(), screen_center.y(), screen_index=screen_index
        )
    return move_mouse_to(960, 540, screen_index=screen_index)


def lock_commands() -> list[list[str]]:
    rundll32 = shutil.which("rundll32.exe") or "rundll32.exe"
    return [[rundll32, "user32.dll,LockWorkStation"]]


def run_lock(commands: list[list[str]]) -> bool:
    try:
        if ctypes.windll.user32.LockWorkStation():
            return True
    except Exception:
        pass
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=PER_COMMAND_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return True
        except OSError:
            continue
        if result.returncode == 0:
            return True
    return False


def power_commands(action: str) -> list[list[str]]:
    candidates = POWER_ACTIONS.get(action, ())
    return [list(command) for command in candidates]


def run_power(commands: list[list[str]]) -> bool:
    for command in commands:
        if any("powrprof" in arg.lower() for arg in command):
            try:
                if ctypes.windll.powrprof.SetSuspendState(0, 1, 0):
                    return True
            except Exception:
                pass
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=PER_COMMAND_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return True
        except OSError:
            continue
        if result.returncode == 0:
            return True
    return False
