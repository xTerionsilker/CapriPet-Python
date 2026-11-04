from __future__ import annotations

import ctypes
import shutil
import subprocess

PER_COMMAND_TIMEOUT_S = 3


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
