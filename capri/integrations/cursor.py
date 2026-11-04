from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QPoint
from PySide6.QtGui import QCursor


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
