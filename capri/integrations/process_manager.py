from __future__ import annotations

import logging
import os
from typing import Any

import psutil
from rapidfuzz import fuzz

from .app_launcher import phonetic_normalize, translit_ru_to_en
from ..commands.registry import switch_layout

logger = logging.getLogger(__name__)


def get_running_processes() -> list[dict[str, Any]]:
    """Возвращает список запущенных процессов кроссплатформенно через psutil."""
    processes: list[dict[str, Any]] = []

    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        try:
            info = proc.info
            pid = info.get("pid")
            name = info.get("name") or ""
            cmdline = info.get("cmdline") or []
            cmd = " ".join(cmdline) if cmdline else name

            if pid is not None and (name or cmd):
                processes.append({
                    "pid": pid,
                    "name": name or os.path.basename(cmdline[0] if cmdline else ""),
                    "comm": name,
                    "cmd": cmd,
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as exc:
            logger.debug("Ошибка при чтении процесса: %s", exc)
            continue

    return processes


def _score_candidate(query: str, target: str) -> float:
    q = query.lower()
    t = target.lower()

    if q == t:
        return 100.0
    if q in t:
        return 80.0 + (len(q) / max(len(t), 1)) * 15.0

    ratio = fuzz.WRatio(q, t)

    q_trans = translit_ru_to_en(q)
    t_trans = translit_ru_to_en(t)
    if q_trans == t_trans:
        return max(ratio, 95.0)
    if q_trans in t_trans:
        ratio = max(ratio, 75.0 + (len(q_trans) / max(len(t_trans), 1)) * 15.0)

    ratio = max(ratio, fuzz.WRatio(q_trans, t_trans))

    q_layout = switch_layout(q)
    if q_layout in t:
        ratio = max(ratio, 70.0)

    q_norm = phonetic_normalize(q_trans)
    t_norm = phonetic_normalize(t_trans)
    if q_norm and t_norm:
        if q_norm == t_norm:
            return max(ratio, 90.0)
        ratio = max(ratio, fuzz.WRatio(q_norm, t_norm))

    return ratio


def _score_process_group(query: str, name: str, cmds: list[str]) -> float:

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


    cur_pid = os.getpid()


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
    """Завершает все процессы из группы через psutil. Возвращает (успех, количество_завершённых)."""
    pids = group.get("pids", [])
    if not pids:
        return False, 0

    killed_count = 0
    for pid in pids:
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as exc:
            logger.debug("Ошибка при завершении процесса PID %s: %s", pid, exc)
            continue

    return killed_count > 0, killed_count
