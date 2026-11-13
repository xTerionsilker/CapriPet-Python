"""Поиск и запуск установленных приложений в операционной системе Windows.

Модуль сканирует ярлыки меню «Пуск» и системный реестр (App Paths),
выполняет нечеткий поиск программ с учетом русской транслитерации,
ошибок раскладки клавиатуры и фонетической нормализации, а также
осуществляет запуск выбранных приложений.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore[assignment]

import cyrtranslit
from rapidfuzz import fuzz

from ..commands.registry import switch_layout

logger = logging.getLogger(__name__)

ALLOWED_LAUNCH_EXTENSIONS: tuple[str, ...] = (
    ".exe",
    ".lnk",
)

BLOCKED_SCRIPT_EXTENSIONS: tuple[str, ...] = (
    ".bat",
    ".cmd",
    ".vbs",
    ".vbe",
    ".js",
    ".jse",
    ".wsf",
    ".wsh",
    ".ps1",
    ".ps1xml",
    ".ps2",
    ".msc",
    ".scr",
    ".pif",
)

BLOCKED_INTERPRETERS: frozenset[str] = frozenset(
    {
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",
        "cscript.exe",
        "wscript.exe",
        "mshta.exe",
        "rundll32.exe",
        "regsvr32.exe",
    }
)


def resolve_shortcut(lnk_path: str) -> tuple[str, str] | None:
    """Извлекает целевой путь и аргументы из ярлыка .lnk с проверкой безопасности."""
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(lnk_path))
        target = str(shortcut.TargetPath).strip()
        args = str(shortcut.Arguments).strip()
        if not target or target.startswith(("\\\\", "//")):
            return None
        target_name = os.path.basename(target).lower()
        if target_name in BLOCKED_INTERPRETERS:
            return None
        ext = os.path.splitext(target)[1].lower()
        if ext in BLOCKED_SCRIPT_EXTENSIONS or ext != ".exe":
            return None
        return target, args
    except Exception as exc:
        logger.debug("Не удалось разобрать ярлык %s: %s", lnk_path, exc)
        return None


def translit_ru_to_en(text: str) -> str:
    t = text.lower().replace("кс", "x")
    return cyrtranslit.to_latin(t, "ru")


def phonetic_normalize(text: str) -> str:
    s = text.lower()
    res: list[str] = []
    for i, ch in enumerate(s):
        if ch == "c":
            if i + 1 < len(s) and s[i + 1] in ("e", "i", "y"):
                res.append("s")
            else:
                res.append("k")
        elif ch in ("q", "k"):
            res.append("k")
        elif ch == "x":
            res.extend(["k", "s"])
        elif ch == "w":
            res.append("v")
        else:
            res.append(ch)
    normalized = "".join(res)
    return re.sub(r"([a-z])\1+", r"\1", normalized)


def _scan_windows_applications() -> list[dict[str, Any]]:
    apps: dict[str, dict[str, Any]] = {}

    start_dirs = [
        os.path.expandvars(
            r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"
        ),
        os.path.expandvars(
            r"%AppData%\Microsoft\Windows\Start Menu\Programs"
        ),
    ]
    for sdir in start_dirs:
        if not os.path.exists(sdir):
            continue
        for root, _, files in os.walk(sdir):
            for f in files:
                if f.lower().endswith(".lnk"):
                    full_lnk = os.path.join(root, f)
                    res = resolve_shortcut(full_lnk)
                    if res is not None:
                        target_path, _ = res
                        if os.path.isfile(target_path):
                            name = os.path.splitext(f)[0]
                            if name.lower() not in apps:
                                apps[name.lower()] = {
                                    "name": name,
                                    "exec": full_lnk,
                                    "comment": "",
                                    "path": target_path,
                                }

    if winreg is not None:
        for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                sub = (
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
                )
                with winreg.OpenKey(hkey, sub) as key:
                    count, _, _ = winreg.QueryInfoKey(key)
                    for i in range(count):
                        try:
                            app_key_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(
                                key, app_key_name
                            ) as app_key:
                                val, _ = winreg.QueryValueEx(app_key, "")
                                if val and os.path.exists(val):
                                    display_name = os.path.splitext(
                                        app_key_name
                                    )[0]
                                    if display_name.lower() not in apps:
                                        apps[display_name.lower()] = {
                                            "name": display_name,
                                            "exec": val,
                                            "comment": "",
                                            "path": val,
                                        }
                        except OSError:
                            pass
            except OSError:
                pass

    return list(apps.values())


def get_installed_applications() -> list[dict[str, Any]]:
    return _scan_windows_applications()


def _score_application(query: str, app: dict[str, Any]) -> float:
    q = query.lower().strip()
    raw_candidates = {q, translit_ru_to_en(q), switch_layout(q)}
    candidates = set(raw_candidates)
    for c in raw_candidates:
        if c:
            candidates.add(phonetic_normalize(c))
    candidates.discard("")

    name = app.get("name", "").lower().strip()
    exec_str = app.get("exec", "")
    exec_parts = exec_str.strip().split()
    exec_bin = os.path.basename(exec_parts[0]) if exec_parts else ""
    exec_base = re.sub(r"\.(exe|desktop)$", "", exec_bin.lower())
    comment = app.get("comment", "").lower()

    for cand in candidates:
        if cand in (name, exec_base):
            return 100.0

    best = 0.0

    name_tokens = re.split(r"[\s\-_\.]+", f"{name} {exec_base}")
    for token in name_tokens:
        if not token:
            continue
        p_token = phonetic_normalize(token)
        for cand in candidates:
            if cand in (token, p_token):
                score = 95.0
            elif token.startswith(cand) or p_token.startswith(cand):
                score = 80.0 + (len(cand) / max(len(token), 1)) * 15.0
            elif (cand.startswith((token, p_token))) and len(token) >= 3:
                score = 75.0 + (len(token) / max(len(cand), 1)) * 15.0
            elif (cand in token or cand in p_token) and len(cand) >= 3:
                score = 70.0 + (len(cand) / max(len(token), 1)) * 15.0
            else:
                ratio = max(
                    fuzz.ratio(cand, token) / 100.0,
                    fuzz.ratio(cand, p_token) / 100.0,
                )
                score = ratio * 70.0

            best = max(best, score)

    comment_tokens = re.split(r"[\s\-_\.]+", comment)
    for token in comment_tokens:
        if not token:
            continue
        p_token = phonetic_normalize(token)
        for cand in candidates:
            if cand in (token, p_token):
                score = 65.0
            elif token.startswith(cand) and len(cand) >= 3:
                score = 55.0
            else:
                ratio = max(
                    fuzz.ratio(cand, token) / 100.0,
                    fuzz.ratio(cand, p_token) / 100.0,
                )
                score = ratio * 40.0

            best = max(best, score)

    return best


def find_matching_applications(
    query: str, limit: int = 5
) -> list[dict[str, Any]]:
    trimmed = query.strip()
    if not trimmed:
        return []

    apps = get_installed_applications()
    scored: list[tuple[float, dict[str, Any]]] = []
    for app in apps:
        score = _score_application(trimmed, app)
        if score >= 25.0:
            scored.append((score, app))

    scored.sort(key=lambda x: x[0], reverse=True)

    seen_names: set[str] = set()
    result: list[dict[str, Any]] = []
    for _, app in scored:
        name_key = app["name"].lower()
        if name_key not in seen_names:
            seen_names.add(name_key)
            result.append(app)
            if len(result) >= limit:
                break

    return result


def is_safe_executable_path(path_str: str) -> bool:
    """Проверяет безопасность расширения и существование исполняемого файла."""
    if not path_str or not isinstance(path_str, str):
        return False

    clean_path = path_str.strip().strip('"').strip("'")
    if not clean_path:
        return False

    ext = os.path.splitext(clean_path)[1].lower()
    if ext in BLOCKED_SCRIPT_EXTENSIONS:
        logger.warning(
            "Заблокирован запуск опасного сценария (%s): %s", ext, clean_path
        )
        return False

    if ext not in ALLOWED_LAUNCH_EXTENSIONS:
        logger.warning(
            "Заблокирован запуск неподдерживаемого расширения (%s): %s",
            ext,
            clean_path,
        )
        return False

    if not os.path.isfile(clean_path):
        logger.warning("Исполняемый файл не найден: %s", clean_path)
        return False

    if ext == ".lnk":
        resolved = resolve_shortcut(clean_path)
        if resolved is None:
            return False
        target_path, _ = resolved
        target_name = os.path.basename(target_path).lower()
        if target_name in BLOCKED_INTERPRETERS:
            logger.warning(
                "Заблокирован запуск системного интерпретатора через ярлык: %s",
                target_path,
            )
            return False
        return is_safe_executable_path(target_path)

    return True


def launch_application(app: dict[str, Any]) -> bool:
    """Безопасно запускает проверенный бинарный файл или ярлык."""
    exec_cmd = app.get("exec", "")
    if not exec_cmd or not is_safe_executable_path(exec_cmd):
        return False

    clean_path = exec_cmd.strip().strip('"').strip("'")
    try:
        os.startfile(clean_path)
        return True
    except OSError as e:
        logger.warning("Не удалось запустить приложение %s: %s", clean_path, e)
        return False
