from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QCursor, QGuiApplication

logger = logging.getLogger(__name__)


def get_active_window_rect() -> QRect | None:
    """Возвращает прямоугольник QRect активного окна пользователя.

    Поддерживает:
    - Windows (через Win32 API GetForegroundWindow / GetWindowRect)
    - Linux KDE Plasma Wayland (через KWin Scripting)
    - Linux X11 (через xdotool / xprop)
    - Фолбэк на экран, где расположен курсор пользователя.
    """
    if sys.platform == "win32":
        rect = _get_windows_active_window_rect()
        if rect is not None and rect.isValid():
            return rect

    if sys.platform.startswith("linux"):
        # 1. Если KDE Wayland / KWin
        rect = _get_kwin_active_window_rect()
        if rect is not None and rect.isValid():
            return rect

        # 2. Если X11 / XWayland с xdotool
        rect = _get_x11_active_window_rect()
        if rect is not None and rect.isValid():
            return rect

    # Фолбэк: определяем экран, на котором находится курсор
    return get_active_screen_rect()


def get_active_screen_rect() -> QRect:
    """Возвращает геометрию экрана, на котором сейчас находится курсор мыши."""
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
        import ctypes
        from ctypes import wintypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        # Проверяем, не свернуто ли окно
        if user32.IsIconic(hwnd):
            return None

        rect = RECT()
        # Попытка получить точные границы с учётом DwmGetWindowAttribute
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


def _get_kwin_active_window_rect() -> QRect | None:
    """Получает координаты активного окна через интерфейс KWin Scripting."""
    qdbus = shutil.which("qdbus6") or shutil.which("qdbus")
    if not qdbus:
        return None

    tag = "CP_WIN_" + uuid.uuid4().hex[:8]
    # KWin Script: получаем геометрию workspace.activeWindow
    script_content = (
        f'var w = workspace.activeWindow;\n'
        f'if (w) {{\n'
        f'    console.log("{tag}:" + Math.round(w.x) + "," + Math.round(w.y) + "," + Math.round(w.width) + "," + Math.round(w.height));\n'
        f'}}\n'
    )
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(script_content)
            tmp_path = f.name

        res = subprocess.check_output(
            [qdbus, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.loadScript", tmp_path],
            text=True,
            timeout=0.6,
        ).strip()

        script_num = res
        subprocess.run(
            [qdbus, "org.kde.KWin", f"/Scripting/Script{script_num}", "org.kde.kwin.Script.run"],
            timeout=0.4,
            check=False,
        )
        subprocess.run(
            [qdbus, "org.kde.KWin", f"/Scripting/Script{script_num}", "org.kde.kwin.Script.stop"],
            timeout=0.4,
            check=False,
        )

        logs = subprocess.check_output(
            ["journalctl", "--user", "-u", "plasma-kwin_wayland", "-n", "15", "--no-pager"],
            text=True,
            timeout=0.8,
        )

        for line in reversed(logs.splitlines()):
            if tag in line:
                coords = line.split(f"{tag}:")[1].strip()
                parts = coords.split(",")
                if len(parts) == 4:
                    x, y, w, h = map(int, parts)
                    if w > 50 and h > 50:
                        return QRect(x, y, w, h)
    except Exception as e:
        logger.debug("KWin script active window query failed: %s", e)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return None


def _get_x11_active_window_rect() -> QRect | None:
    """Получает координаты активного окна через xdotool в окружении X11."""
    xdotool = shutil.which("xdotool")
    if not xdotool:
        return None
    try:
        window_id = subprocess.check_output(
            [xdotool, "getactivewindow"],
            text=True,
            timeout=0.4,
        ).strip()
        if not window_id:
            return None

        geom_output = subprocess.check_output(
            [xdotool, "getwindowgeometry", "--shell", window_id],
            text=True,
            timeout=0.4,
        )
        props: dict[str, int] = {}
        for line in geom_output.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                try:
                    props[k.strip()] = int(v.strip())
                except ValueError:
                    pass

        x = props.get("X")
        y = props.get("Y")
        w = props.get("WIDTH")
        h = props.get("HEIGHT")
        if x is not None and y is not None and w is not None and h is not None:
            if w > 50 and h > 50:
                return QRect(x, y, w, h)
    except Exception as e:
        logger.debug("xdotool active window query failed: %s", e)
    return None
