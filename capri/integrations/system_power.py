from __future__ import annotations

import ctypes
import subprocess

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
