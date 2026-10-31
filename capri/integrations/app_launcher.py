from __future__ import annotations

import configparser
import difflib
import os
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any

from ..commands.registry import switch_layout

RUS_TO_ENG = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ы": "y", "э": "e", "ю": "yu", "я": "ya", "ъ": "", "ь": "",
}


def translit_ru_to_en(text: str) -> str:
    t = text.lower().replace("кс", "x")
    return "".join(RUS_TO_ENG.get(ch, ch) for ch in t)


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


def _clean_exec_command(exec_str: str) -> list[str]:
    """Удаляет desktop spec field codes (%f, %F, %u, %U и т.д.) и разбивает команду на аргументы."""
    cleaned = re.sub(r"%[a-zA-Z]", "", exec_str).strip()
    try:
        parts = shlex.split(cleaned)
    except Exception:
        parts = cleaned.split()
    return parts


def _scan_linux_applications() -> list[dict[str, Any]]:
    desktop_dirs = [
        "/usr/share/applications",
        "/usr/local/share/applications",
        os.path.expanduser("~/.local/share/applications"),
    ]
    apps: dict[str, dict[str, Any]] = {}
    for base_dir in desktop_dirs:
        if not os.path.exists(base_dir):
            continue
        for root, _, files in os.walk(base_dir):
            for file_name in files:
                if not file_name.endswith(".desktop"):
                    continue
                file_path = os.path.join(root, file_name)
                cp = configparser.ConfigParser(interpolation=None)
                try:
                    cp.read(file_path, encoding="utf-8")
                    if "Desktop Entry" not in cp:
                        continue
                    sec = cp["Desktop Entry"]
                    if sec.get("NoDisplay", "false").lower() == "true":
                        continue
                    if sec.get("Type", "Application") != "Application":
                        continue
                    name = sec.get("Name")
                    exec_cmd = sec.get("Exec")
                    if not name or not exec_cmd:
                        continue
                    comment = sec.get("Comment", "")
                    if file_name not in apps:
                        apps[file_name] = {
                            "name": name,
                            "exec": exec_cmd,
                            "comment": comment,
                            "path": file_path,
                        }
                except Exception:
                    pass
    return list(apps.values())


def _scan_windows_applications() -> list[dict[str, Any]]:
    apps: dict[str, dict[str, Any]] = {}

    start_dirs = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
    ]
    for sdir in start_dirs:
        if not os.path.exists(sdir):
            continue
        for root, _, files in os.walk(sdir):
            for f in files:
                if f.lower().endswith(".lnk"):
                    name = os.path.splitext(f)[0]
                    if name.lower() not in apps:
                        apps[name.lower()] = {
                            "name": name,
                            "exec": os.path.join(root, f),
                            "comment": "",
                            "path": os.path.join(root, f),
                        }

    try:
        import winreg  # type: ignore

        for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
                with winreg.OpenKey(hkey, sub) as key:
                    count, _, _ = winreg.QueryInfoKey(key)
                    for i in range(count):
                        try:
                            app_key_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, app_key_name) as app_key:
                                val, _ = winreg.QueryValueEx(app_key, "")
                                if val and os.path.exists(val):
                                    display_name = os.path.splitext(app_key_name)[0]
                                    if display_name.lower() not in apps:
                                        apps[display_name.lower()] = {
                                            "name": display_name,
                                            "exec": val,
                                            "comment": "",
                                            "path": val,
                                        }
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass

    return list(apps.values())


def get_installed_applications() -> list[dict[str, Any]]:
    """Возвращает список установленных в системе приложений."""
    if sys.platform == "win32":
        return _scan_windows_applications()
    return _scan_linux_applications()


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

    # Точные совпадения целиком
    for cand in candidates:
        if cand == name or cand == exec_base:
            return 100.0

    best = 0.0

    # Проверка слов в названии и исполняемом файле
    name_tokens = re.split(r"[\s\-_\.]+", f"{name} {exec_base}")
    for token in name_tokens:
        if not token:
            continue
        p_token = phonetic_normalize(token)
        for cand in candidates:
            if cand == token or cand == p_token:
                score = 95.0
            elif token.startswith(cand) or p_token.startswith(cand):
                score = 80.0 + (len(cand) / max(len(token), 1)) * 15.0
            elif (cand.startswith(token) or cand.startswith(p_token)) and len(token) >= 3:
                score = 75.0 + (len(token) / max(len(cand), 1)) * 15.0
            elif (cand in token or cand in p_token) and len(cand) >= 3:
                score = 70.0 + (len(cand) / max(len(token), 1)) * 15.0
            else:
                ratio = max(
                    difflib.SequenceMatcher(None, cand, token).ratio(),
                    difflib.SequenceMatcher(None, cand, p_token).ratio(),
                )
                score = ratio * 70.0

            if score > best:
                best = score

    # Проверка слов в описании (comment)
    comment_tokens = re.split(r"[\s\-_\.]+", comment)
    for token in comment_tokens:
        if not token:
            continue
        p_token = phonetic_normalize(token)
        for cand in candidates:
            if cand == token or cand == p_token:
                score = 65.0
            elif token.startswith(cand) and len(cand) >= 3:
                score = 55.0
            else:
                ratio = max(
                    difflib.SequenceMatcher(None, cand, token).ratio(),
                    difflib.SequenceMatcher(None, cand, p_token).ratio(),
                )
                score = ratio * 40.0

            if score > best:
                best = score

    return best


def find_matching_applications(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Находит до `limit` наиболее подходящих под запрос приложений."""
    trimmed = query.strip()
    if not trimmed:
        return []

    apps = get_installed_applications()
    scored: list[tuple[float, dict[str, Any]]] = []
    for app in apps:
        score = _score_application(trimmed, app)
        if score >= 25.0:  # порог релевантности
            scored.append((score, app))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Убираем дубликаты по названию
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


def launch_application(app: dict[str, Any]) -> bool:
    """Запускает выбранное приложение."""
    exec_cmd = app.get("exec", "")
    if not exec_cmd:
        return False

    try:
        if sys.platform == "win32":
            os.startfile(exec_cmd)  # type: ignore[attr-defined]
            return True

        cmd_parts = _clean_exec_command(exec_cmd)
        if not cmd_parts:
            return False

        subprocess.Popen(
            cmd_parts,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception:
        if sys.platform != "win32" and "path" in app:
            desktop_name = os.path.basename(app["path"])
            if shutil.which("gtk-launch"):
                try:
                    subprocess.Popen(
                        ["gtk-launch", desktop_name],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    return True
                except Exception:
                    pass
        return False
