from __future__ import annotations

import os
import shutil
import subprocess
import sys

PER_COMMAND_TIMEOUT_S = 3


def lock_commands() -> list[list[str]]:
    if sys.platform == "win32":
        rundll32 = shutil.which("rundll32.exe") or "rundll32.exe"
        return [[rundll32, "user32.dll,LockWorkStation"]]

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

    candidates.append(["loginctl", "lock-session"])
    candidates.append(["xdg-screensaver", "lock"])
    candidates.append(["gnome-screensaver-command", "-l"])
    candidates.append(["cinnamon-screensaver-command", "-l"])
    candidates.append(["xfce4-screensaver-command", "-l"])
    candidates.append(["light-locker-command", "-l"])

    return [command for command in candidates if shutil.which(command[0])]


def run_lock(commands: list[list[str]]) -> bool:
    if sys.platform == "win32":
        try:
            import ctypes

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
