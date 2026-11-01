from __future__ import annotations

import difflib
import os
import signal
import subprocess
import sys
from typing import Any

from .app_launcher import phonetic_normalize, translit_ru_to_en
from ..commands.registry import switch_layout


def get_running_processes() -> list[dict[str, Any]]:
    """Возвращает список запущенных процессов для Linux и Windows."""
    if sys.platform == "win32":
        return _get_running_processes_windows()
    return _get_running_processes_linux()


def _get_running_processes_linux() -> list[dict[str, Any]]:
    processes: list[dict[str, Any]] = []

    # 1. Сначала пробуем ps -eo pid,comm,args
    try:
        res = subprocess.run(
            ["ps", "-eo", "pid,comm,args"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        if res.returncode == 0:
            lines = res.stdout.splitlines()
            if lines:
                lines = lines[1:]  # пропускаем заголовок
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 2)
                if not parts or not parts[0].isdigit():
                    continue
                pid = int(parts[0])
                comm = parts[1] if len(parts) > 1 else ""
                args = parts[2] if len(parts) > 2 else comm
                name = os.path.basename(comm or args.split()[0] if args else "")
                processes.append({
                    "pid": pid,
                    "name": name,
                    "comm": comm,
                    "cmd": args,
                })
            if processes:
                return processes
    except Exception:
        pass

    # 2. Фолбэк на /proc
    if os.path.isdir("/proc"):
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            pid = int(entry)
            comm = ""
            cmd = ""
            try:
                comm_path = os.path.join("/proc", entry, "comm")
                if os.path.isfile(comm_path):
                    with open(comm_path, "r", encoding="utf-8", errors="ignore") as f:
                        comm = f.read().strip()
                cmdline_path = os.path.join("/proc", entry, "cmdline")
                if os.path.isfile(cmdline_path):
                    with open(cmdline_path, "rb") as f:
                        raw = f.read()
                        cmd = raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip()
            except Exception:
                continue

            name = comm or (os.path.basename(cmd.split()[0]) if cmd else "")
            if name:
                processes.append({
                    "pid": pid,
                    "name": name,
                    "comm": comm,
                    "cmd": cmd or comm,
                })

    return processes


def _get_running_processes_windows() -> list[dict[str, Any]]:
    processes: list[dict[str, Any]] = []
    try:
        import csv
        res = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3.0,
        )
        if res.returncode == 0:
            reader = csv.reader(res.stdout.splitlines())
            for row in reader:
                if len(row) >= 2:
                    image_name = row[0].strip()
                    pid_str = row[1].strip()
                    if pid_str.isdigit():
                        processes.append({
                            "pid": int(pid_str),
                            "name": image_name,
                            "comm": image_name,
                            "cmd": image_name,
                        })
    except Exception:
        pass
    return processes


def _score_candidate(query: str, target: str) -> float:
    q = query.lower()
    t = target.lower()

    if q == t:
        return 100.0
    if q in t:
        return 80.0 + (len(q) / max(len(t), 1)) * 15.0

    ratio = difflib.SequenceMatcher(None, q, t).ratio() * 100.0

    q_trans = translit_ru_to_en(q)
    t_trans = translit_ru_to_en(t)
    if q_trans == t_trans:
        return max(ratio, 95.0)
    if q_trans in t_trans:
        ratio = max(ratio, 75.0 + (len(q_trans) / max(len(t_trans), 1)) * 15.0)

    trans_ratio = difflib.SequenceMatcher(None, q_trans, t_trans).ratio() * 100.0
    ratio = max(ratio, trans_ratio)

    q_layout = switch_layout(q)
    if q_layout in t:
        ratio = max(ratio, 70.0)

    q_norm = phonetic_normalize(q_trans)
    t_norm = phonetic_normalize(t_trans)
    if q_norm and t_norm:
        if q_norm == t_norm:
            return max(ratio, 90.0)
        norm_ratio = difflib.SequenceMatcher(None, q_norm, t_norm).ratio() * 100.0
        ratio = max(ratio, norm_ratio)

    return ratio


def _score_process_group(query: str, name: str, cmds: list[str]) -> float:
    # Очищаем расширение .exe при сопоставлении
    clean_name = name
    if clean_name.lower().endswith(".exe"):
        clean_name = clean_name[:-4]

    scores = [_score_candidate(query, clean_name), _score_candidate(query, name)]
    for cmd in cmds[:5]:
        first_token = os.path.basename(cmd.split()[0]) if cmd else ""
        if first_token.lower().endswith(".exe"):
            first_token = first_token[:-4]
        if first_token:
            scores.append(_score_candidate(query, first_token))

    return max(scores) if scores else 0.0


def find_matching_processes(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Находит процессы по названию, группирует их по имени процесса и возвращает топ-5."""
    trimmed = query.strip()
    if not trimmed:
        return []

    processes = get_running_processes()
    if not processes:
        return []

    # Текущий процесс CapriPet не предлагаем убивать
    cur_pid = os.getpid()

    # Группировка процессов по имени
    groups: dict[str, dict[str, Any]] = {}
    for p in processes:
        if p["pid"] == cur_pid:
            continue
        name = p["name"] or "unknown"
        if name not in groups:
            groups[name] = {
                "name": name,
                "pids": [],
                "cmds": [],
            }
        groups[name]["pids"].append(p["pid"])
        if p.get("cmd") and len(groups[name]["cmds"]) < 5:
            groups[name]["cmds"].append(p["cmd"])

    scored: list[tuple[float, dict[str, Any]]] = []
    for name, group in groups.items():
        score = _score_process_group(trimmed, name, group["cmds"])
        if score >= 25.0:
            scored.append((score, group))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [grp for _, grp in scored[:limit]]


def kill_process_group(group: dict[str, Any]) -> tuple[bool, int]:
    """Завершает все процессы из группы. Возвращает (успех, количество_завершённых)."""
    pids = group.get("pids", [])
    if not pids:
        return False, 0

    killed_count = 0
    if sys.platform == "win32":
        name = group.get("name", "")
        # Пробуем через taskkill /IM <name> /F
        if name:
            try:
                res = subprocess.run(
                    ["taskkill", "/F", "/IM", name],
                    capture_output=True,
                    check=False,
                    timeout=3.0,
                )
                if res.returncode == 0:
                    return True, len(pids)
            except Exception:
                pass

        # Иначе убиваем по PID
        for pid in pids:
            try:
                res = subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    check=False,
                    timeout=2.0,
                )
                if res.returncode == 0:
                    killed_count += 1
            except Exception:
                pass
        return killed_count > 0, killed_count

    # Linux: kill SIGTERM -> SIGKILL
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            killed_count += 1
        except ProcessLookupError:
            pass
        except PermissionError:
            pass
        except Exception:
            pass

    return killed_count > 0, killed_count
