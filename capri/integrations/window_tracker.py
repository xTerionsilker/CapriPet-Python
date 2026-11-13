"""Отслеживание активных окон и управление их положением в Windows.

Содержит вспомогательные функции для получения дескриптора (HWND) и геометрии
активного окна пользователя, анимации встряхивания внешнего окна через Win32 API
и определения координат активного монитора.
"""

from __future__ import annotations

import contextlib
import logging
import random
from collections.abc import Callable

import win32con
import win32gui
from PySide6.QtCore import QObject, QRect, QTimer
from PySide6.QtGui import QCursor, QGuiApplication

logger = logging.getLogger(__name__)


def get_foreground_hwnd() -> int | None:
    """Возвращает валидный HWND активного пользовательского окна (исключая рабочий стол и трей)."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd or not win32gui.IsWindow(hwnd):
            return None
        if win32gui.IsIconic(hwnd):
            return None

        # Игнорируем рабочий стол
        if hwnd == win32gui.GetDesktopWindow():
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
        if not win32gui.IsWindow(hwnd):
            if on_finished:
                on_finished()
            return None

        left, top, _right, _bottom = win32gui.GetWindowRect(hwnd)
        orig_x, orig_y = left, top
        flags = win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE

        interval_ms = 25
        total_steps = max(1, duration_ms // interval_ms)
        step = 0

        timer = QTimer(parent)
        timer.setInterval(interval_ms)

        def _tick() -> None:
            nonlocal step
            step += 1
            if step >= total_steps or not win32gui.IsWindow(hwnd):
                timer.stop()
                timer.deleteLater()
                with contextlib.suppress(Exception):
                    win32gui.SetWindowPos(
                        hwnd, 0, orig_x, orig_y, 0, 0, flags
                    )
                if on_finished:
                    on_finished()
                return

            dx = random.randint(-intensity, intensity)
            dy = random.randint(-intensity, intensity)
            with contextlib.suppress(Exception):
                win32gui.SetWindowPos(
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
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd or not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):
            return None

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        w = right - left
        h = bottom - top
        if w > 50 and h > 50:
            return QRect(left, top, w, h)
    except Exception as e:
        logger.debug("Windows get_foreground_window failed: %s", e)
    return None
