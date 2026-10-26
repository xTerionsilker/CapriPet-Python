from __future__ import annotations

import os
import shutil
import subprocess
import uuid

from PySide6.QtCore import QPoint
from PySide6.QtGui import QCursor


def get_mouse_position() -> QPoint:
    """Возвращает глобальные координаты мыши с поддержкой Wayland (KWin) и X11."""
    # 1. Сначала пробуем получить координаты через KWin Wayland DBus (KDE Plasma)
    kwin_pos = _get_kwin_mouse_position()
    if kwin_pos is not None:
        return kwin_pos

    # 2. Фолбэк на стандартный QCursor.pos()
    pos = QCursor.pos()
    # Проверка на валидность (в Wayland без прав чтения часто возвращаются 0,0 или гигантские числа)
    if pos.x() < 50000 and pos.y() < 50000:
        return pos

    return pos


def move_mouse_to(x: int, y: int) -> bool:
    """Перемещает курсор мыши в точку (x, y) с поддержкой X11, Wayland, ydotool и xdotool."""
    # 1. Стандартный Qt QCursor.setPos (отлично работает в X11/XWayland)
    try:
        QCursor.setPos(x, y)
        pos = QCursor.pos()
        if abs(pos.x() - x) < 10 and abs(pos.y() - y) < 10:
            return True
    except Exception:
        pass

    # 2. xdotool (если доступен в X11/XWayland)
    if shutil.which("xdotool"):
        try:
            res = subprocess.run(
                ["xdotool", "mousemove", str(x), str(y)],
                check=False,
                timeout=0.3,
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 3. ydotool (Wayland uinput)
    if shutil.which("ydotool"):
        try:
            res = subprocess.run(
                ["ydotool", "mousemove", "--absolute", str(x), str(y)],
                check=False,
                timeout=0.3,
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 4. KWin Scripting для KDE Wayland
    if _set_kwin_mouse_position(x, y):
        return True

    # 5. Фолбэк на KWin шорткат
    _invoke_kwin_shortcut("MoveMouseToCenter")
    return False


def move_mouse_to_center(screen_center: QPoint | None = None) -> bool:
    """Перемещает курсор мыши в центр экрана с поддержкой нескольких мониторов."""
    if screen_center is not None:
        return move_mouse_to(screen_center.x(), screen_center.y())
    return move_mouse_to(960, 540)


def _set_kwin_mouse_position(x: int, y: int) -> bool:
    """Пытается установить координаты курсора через KWin Scripting в KDE Wayland."""
    qdbus = shutil.which("qdbus6") or shutil.which("qdbus")
    if not qdbus:
        return False

    tag = "CP_SET_" + uuid.uuid4().hex[:8]
    script_content = f'workspace.cursorPos = Qt.point({x}, {y});'
    tmp_path = f"/tmp/kwin_set_{tag}.js"

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        res = subprocess.check_output(
            [qdbus, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.loadScript", tmp_path],
            text=True,
            timeout=0.3,
        ).strip()

        script_num = res
        subprocess.run([qdbus, "org.kde.KWin", f"/Scripting/Script{script_num}", "org.kde.kwin.Script.run"], timeout=0.3, check=False)
        subprocess.run([qdbus, "org.kde.KWin", f"/Scripting/Script{script_num}", "org.kde.kwin.Script.stop"], timeout=0.3, check=False)
        return True
    except Exception:
        return False
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _get_kwin_mouse_position() -> QPoint | None:
    """Получает позицию курсора через интерфейс KWin Scripting в KDE Wayland."""
    qdbus = shutil.which("qdbus6") or shutil.which("qdbus")
    if not qdbus:
        return None

    tag = "CP_POS_" + uuid.uuid4().hex[:8]
    script_content = f'console.log("{tag}:" + workspace.cursorPos.x + "," + workspace.cursorPos.y);'
    tmp_path = f"/tmp/kwin_pos_{tag}.js"

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        res = subprocess.check_output(
            [qdbus, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.loadScript", tmp_path],
            text=True,
            timeout=0.3,
        ).strip()

        script_num = res
        subprocess.run([qdbus, "org.kde.KWin", f"/Scripting/Script{script_num}", "org.kde.kwin.Script.run"], timeout=0.3, check=False)
        subprocess.run([qdbus, "org.kde.KWin", f"/Scripting/Script{script_num}", "org.kde.kwin.Script.stop"], timeout=0.3, check=False)

        logs = subprocess.check_output(
            ["journalctl", "--user", "-u", "plasma-kwin_wayland", "-n", "8", "--no-pager"],
            text=True,
            timeout=0.4,
        )

        for line in reversed(logs.splitlines()):
            if tag in line:
                coords = line.split(f"{tag}:")[1].strip()
                x_str, y_str = coords.split(",")
                return QPoint(int(x_str), int(y_str))
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return None


def _invoke_kwin_shortcut(shortcut_name: str) -> bool:
    qdbus = shutil.which("qdbus6") or shutil.which("qdbus")
    if not qdbus:
        return False
    try:
        res = subprocess.run(
            [qdbus, "org.kde.kglobalaccel", "/component/kwin", "org.kde.kglobalaccel.Component.invokeShortcut", shortcut_name],
            check=False,
            timeout=0.5,
        )
        return res.returncode == 0
    except Exception:
        return False
