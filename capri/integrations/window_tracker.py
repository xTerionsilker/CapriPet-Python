from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging

from PySide6.QtCore import QRect
from PySide6.QtGui import QCursor, QGuiApplication

logger = logging.getLogger(__name__)


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def get_active_window_rect() -> QRect | None:
    rect = _get_windows_active_window_rect()
    if rect is not None and rect.isValid():
        return rect
    return get_active_screen_rect()


def get_active_screen_rect() -> QRect:
    cursor_pos = QCursor.pos()
    for screen in QGuiApplication.screens():
        if screen.geometry().contains(cursor_pos):
            return screen.geometry()
    primary = QGuiApplication.primaryScreen()
    if primary:
        return primary.geometry()
    return QRect(0, 0, 1920, 1080)


def _get_windows_active_window_rect() -> QRect | None:
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        if user32.IsIconic(hwnd):
            return None

        rect = _RECT()

        try:
            dwmapi = ctypes.windll.dwmapi
            DWMWA_EXTENDED_FRAME_BOUNDS = 9
            res = dwmapi.DwmGetWindowAttribute(
                hwnd,
                DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(rect),
                ctypes.sizeof(rect),
            )
            if res == 0:
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 50 and h > 50:
                    return QRect(rect.left, rect.top, w, h)
        except Exception:
            pass

        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 50 and h > 50:
                return QRect(rect.left, rect.top, w, h)
    except Exception as e:
        logger.debug("Windows get_foreground_window failed: %s", e)
    return None
