from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
from typing import Optional

from ..core.settings import get_config_value

logger = logging.getLogger(__name__)

_resolved_user_agent: Optional[str] = None
_lock = threading.Lock()


def _get_os_family() -> tuple[str, str]:
    """Возвращает кортеж (тип_системы, платформа_для_UA)."""
    system = platform.system()
    machine = platform.machine()
    is_64 = sys.maxsize > 2**32 or "64" in machine

    if system == "Windows":
        arch_str = "Win64; x64" if is_64 else "Win32"
        return "Windows", f"Windows NT 10.0; {arch_str}"
    if system == "Darwin":
        return "Darwin", "Macintosh; Intel Mac OS X 10_15_7"
    arch_str = "x86_64" if is_64 else machine
    return "Linux", f"X11; Linux {arch_str}"


def _detect_browser_version() -> tuple[str, str]:
    """
    Пытается определить установленный/дефолтный браузер и его версию.
    Возвращает (браузер, версия).
    Поддерживает: 'firefox', 'chrome', 'edge', 'chromium', 'brave'.
    """
    # 1. Если Linux, проверяем xdg-settings / mimeapps
    preferred_browser = None
    if sys.platform.startswith("linux"):
        try:
            res = subprocess.run(
                ["xdg-settings", "get", "default-web-browser"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if res.returncode == 0 and res.stdout.strip():
                preferred_browser = res.stdout.strip().lower()
        except Exception:
            pass

    # Кандидаты для проверки:
    browser_commands = [
        ("firefox", ["firefox", "firefox-bin", "firefox-esr"]),
        ("chrome", ["google-chrome", "google-chrome-stable"]),
        ("edge", ["microsoft-edge", "microsoft-edge-stable", "msedge"]),
        ("brave", ["brave-browser", "brave"]),
        ("chromium", ["chromium", "chromium-browser"]),
    ]

    # Если xdg указал предпочтительный браузер, поднимаем его в приоритете
    if preferred_browser:
        for b_name, cmds in list(browser_commands):
            if b_name in preferred_browser:
                browser_commands.remove((b_name, cmds))
                browser_commands.insert(0, (b_name, cmds))
                break

    for b_type, cmds in browser_commands:
        for cmd in cmds:
            exe = shutil.which(cmd)
            if not exe:
                continue
            try:
                proc = subprocess.run(
                    [exe, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=1.5,
                )
                output = proc.stdout or proc.stderr
                if not output:
                    continue
                # Извлекаем версию вида 120.0.0.0 или 135.0
                match = re.search(r"(\d+(\.\d+)+)", output)
                if match:
                    version = match.group(1)
                    return b_type, version
            except Exception:
                continue

    # Windows fallback через реестр / известные пути
    if sys.platform == "win32":
        try:
            import winreg

            # Проверяем App Paths или ProgId
            for key_path, b_type in [
                (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe", "chrome"),
                (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe", "edge"),
                (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe", "firefox"),
            ]:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
                        val, _ = winreg.QueryValueEx(k, "")
                        if val and os.path.exists(val):
                            # Простая проверка, если найден chrome/edge/firefox
                            return b_type, "130.0.0.0"
                except OSError:
                    pass
        except Exception:
            pass

    return "chrome", "131.0.0.0"


def _generate_user_agent() -> str:
    """Генерирует актуальный User-Agent на основе ОС и обнаруженного браузера."""
    _, os_ua_part = _get_os_family()
    b_type, b_ver = _detect_browser_version()

    if b_type == "firefox":
        major_ver = b_ver.split(".")[0]
        return f"Mozilla/5.0 ({os_ua_part}; rv:{major_ver}.0) Gecko/20100101 Firefox/{b_ver}"

    if b_type == "edge":
        return (
            f"Mozilla/5.0 ({os_ua_part}) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{b_ver} Safari/537.36 Edg/{b_ver}"
        )

    # По умолчанию для Chromium, Chrome, Brave и fallback
    return (
        f"Mozilla/5.0 ({os_ua_part}) AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{b_ver} Safari/537.36"
    )


def init_user_agent_async() -> None:
    """Асинхронная инициализация User-Agent при запуске приложения."""
    thread = threading.Thread(
        target=get_user_agent,
        name="capri-user-agent-init",
        daemon=True,
    )
    thread.start()


def get_user_agent() -> str:
    """
    Возвращает User-Agent текущего пользователя.
    1. Если задан в конфиге (network.user_agent) — используется он.
    2. Иначе определяется на основе ОС и браузера системы.
    """
    global _resolved_user_agent

    if _resolved_user_agent is not None:
        return _resolved_user_agent

    with _lock:
        if _resolved_user_agent is not None:
            return _resolved_user_agent

        try:
            custom_ua = get_config_value("network.user_agent")
            if custom_ua and isinstance(custom_ua, str) and custom_ua.strip():
                _resolved_user_agent = custom_ua.strip()
                logger.debug("Используется пользовательский User-Agent из конфига: %s", _resolved_user_agent)
                return _resolved_user_agent
        except Exception as e:
            logger.debug("Не удалось прочитать User-Agent из конфига: %s", e)

        try:
            _resolved_user_agent = _generate_user_agent()
            logger.debug("Определен User-Agent системы: %s", _resolved_user_agent)
        except Exception as e:
            logger.warning("Ошибка при автоопределении User-Agent: %s", e)
            _, os_ua_part = _get_os_family()
            _resolved_user_agent = (
                f"Mozilla/5.0 ({os_ua_part}) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )

        return _resolved_user_agent
