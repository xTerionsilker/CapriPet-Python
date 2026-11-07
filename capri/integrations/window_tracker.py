"""Отслеживание активных окон и управление их положением в Windows.

Содержит вспомогательные функции для получения дескриптора (HWND) и геометрии
активного окна пользователя, анимации встряхивания внешнего окна через Win32 API
и определения координат активного монитора.
"""

from __future__ import annotations

import contextlib
import ctypes
import logging
import random
from collections.abc import Callable
from ctypes import wintypes

from PySide6.QtCore import QObject, QRect, QTimer
from PySide6.QtGui import QCursor, QGuiApplication

logger = logging.getLogger(__name__)


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def get_foreground_hwnd() -> int | None:
    """Возвращает валидный HWND активного пользовательского окна (исключая рабочий стол и трей)."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd or not user32.IsWindow(hwnd):
            return None
        if user32.IsIconic(hwnd):
            return None

        # Игнорируем рабочий стол и системный трей
        desktop_hwnd = user32.GetDesktopWindow()
        shell_hwnd = user32.GetShellWindow()
        if hwnd in (desktop_hwnd, shell_hwnd):
            return None

        return int(hwnd)
    except Exception as e:
        logger.debug("get_foreground_hwnd failed: %s", e)
        return None


def shake_window_hwnd(
    hwnd: int,
    duration_ms: int = 700,
    intensity: int = 15,
    on_finished: Callable[[], None] | None = None,
    parent: QObject | None = None,
) -> QTimer | None:
    """Трясет внешнее окно Windows по его HWND через SetWindowPos, восстанавливая исходную позицию."""
    try:
        user32 = ctypes.windll.user32
        if not user32.IsWindow(hwnd):
            if on_finished:
                on_finished()
            return None

        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            if on_finished:
                on_finished()
            return None

        orig_x, orig_y = rect.left, rect.top

        SWP_NOZORDER = 0x0004
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        flags = SWP_NOZORDER | SWP_NOSIZE | SWP_NOACTIVATE

        interval_ms = 25
        total_steps = max(1, duration_ms // interval_ms)
        step = 0

        timer = QTimer(parent)
        timer.setInterval(interval_ms)

        def _tick() -> None:
            nonlocal step
            step += 1
            if step >= total_steps or not user32.IsWindow(hwnd):
                timer.stop()
                timer.deleteLater()
                with contextlib.suppress(Exception):
                    user32.SetWindowPos(
                        hwnd, 0, orig_x, orig_y, 0, 0, flags
                    )
                if on_finished:
                    on_finished()
                return

            dx = random.randint(-intensity, intensity)
            dy = random.randint(-intensity, intensity)
            with contextlib.suppress(Exception):
                user32.SetWindowPos(
                    hwnd, 0, orig_x + dx, orig_y + dy, 0, 0, flags
                )

        timer.timeout.connect(_tick)
        timer.start()
        return timer
    except Exception as e:
        logger.debug("shake_window_hwnd failed: %s", e)
        if on_finished:
            on_finished()
        return None


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
