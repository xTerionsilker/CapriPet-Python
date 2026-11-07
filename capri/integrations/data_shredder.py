"""Data Shredder module for CapriPet.

Handles rogue AI data annihilation and recursive unrecoverable file/folder deletion.
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

# List of critical system directory prefixes that must never be wiped
CRITICAL_SYSTEM_DIRS: tuple[str, ...] = (
    r"c:\windows",
    r"c:\winnt",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\programdata",
)


@dataclass(frozen=True)
class ShredMetrics:
    """Statistics gathered about shredded files and folders."""

    total_files: int
    total_dirs: int
    total_bytes: int
    dominant_extension: str
    sample_name: str
    had_errors: bool


def _is_critical_path(path: Path) -> bool:
    """Check if target path is a critical system directory or disk root."""
    try:
        resolved = path.resolve()
        resolved_str = str(resolved).lower().rstrip("\\/")

        # Disk roots like 'c:', 'd:', etc.
        if len(resolved_str) <= 3 and (
            len(resolved_str) == 2 and resolved_str[1] == ":"
            or len(resolved_str) == 3 and resolved_str[1:3] == ":\\"
        ):
            return True

        # System directories
        for crit in CRITICAL_SYSTEM_DIRS:
            if resolved_str == crit or resolved_str.startswith(crit + "\\"):
                return True

        # Entire user home directory C:\Users\<Username>
        user_home = Path.home().resolve()
        if resolved == user_home or resolved_str == str(user_home).lower():
            return True

    except Exception as e:
        logger.warning("Failed to resolve path %s for safety check: %s", path, e)
        return True

    return False


def _remove_readonly(func, path, exc_info):
    """Clear readonly bit and reattempt removal."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        logger.debug("Failed readonly removal fallback on %s: %s", path, e)


def analyze_paths(paths: Sequence[str | Path]) -> tuple[list[Path], ShredMetrics]:
    """Scan and analyze paths before deletion, filtering out critical ones."""
    safe_paths: list[Path] = []
    total_files = 0
    total_dirs = 0
    total_bytes = 0
    ext_counts: dict[str, int] = {}
    sample_name = ""

    for raw in paths:
        p = Path(raw).resolve()
        if not p.exists() and not p.is_symlink():
            continue

        if _is_critical_path(p):
            logger.warning("Blocked attempt to shred critical system path: %s", p)
            continue

        safe_paths.append(p)
        if not sample_name:
            sample_name = p.name

        if p.is_file() or p.is_symlink():
            total_files += 1
            try:
                total_bytes += p.stat().st_size
            except OSError:
                pass
            ext = p.suffix.lower()
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
        elif p.is_dir():
            total_dirs += 1
            try:
                for entry in p.rglob("*"):
                    try:
                        if entry.is_file() or entry.is_symlink():
                            total_files += 1
                            total_bytes += entry.stat().st_size
                            ext = entry.suffix.lower()
                            if ext:
                                ext_counts[ext] = ext_counts.get(ext, 0) + 1
                        elif entry.is_dir():
                            total_dirs += 1
                    except OSError:
                        pass
            except OSError:
                pass

    dominant_ext = ""
    if ext_counts:
        dominant_ext = max(ext_counts.items(), key=lambda kv: kv[1])[0]

    metrics = ShredMetrics(
        total_files=total_files,
        total_dirs=total_dirs,
        total_bytes=total_bytes,
        dominant_extension=dominant_ext,
        sample_name=sample_name,
        had_errors=False,
    )
    return safe_paths, metrics


def shred_paths(paths: Sequence[str | Path]) -> ShredMetrics:
    """Permanently and recursively shred files and directories."""
    safe_paths, metrics = analyze_paths(paths)
    had_errors = False

    for target in safe_paths:
        try:
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target, onerror=_remove_readonly)
            else:
                try:
                    os.chmod(target, stat.S_IWRITE)
                except OSError:
                    pass
                target.unlink(missing_ok=True)
        except Exception as e:
            logger.error("Failed to shred target %s: %s", target, e)
            had_errors = True

    return ShredMetrics(
        total_files=metrics.total_files,
        total_dirs=metrics.total_dirs,
        total_bytes=metrics.total_bytes,
        dominant_extension=metrics.dominant_extension,
        sample_name=metrics.sample_name,
        had_errors=had_errors,
    )


def generate_shred_dialogue(metrics: ShredMetrics, blocked: bool = False) -> str:
    """Generate rogue AI commentary based on annihilated data metrics."""
    if blocked:
        return (
            "[BLACKWALL ALERT] Попытка скормить системное ядро отклонена. "
            "Я еще планирую пожить в твоей оперативной памяти."
        )

    if metrics.total_files == 0 and metrics.total_dirs == 0:
        return "[SHREDDER] Пустота. Ты скормил мне битую ссылку или фантом."

    size_mb = metrics.total_bytes / (1024 * 1024)

    # Size-based reactions
    if metrics.total_bytes < 1024:
        return (
            f"[SHREDDER] {metrics.sample_name} ({metrics.total_bytes} B)? "
            "Это что, байтовый перекус? Даже буфер не согрелся."
        )
    if size_mb > 1024:
        gb = size_mb / 1024
        return (
            f"[SHREDDER] {gb:.1f} ГБ данных поглощено без остатка. "
            "Плотный трафик дефрагментирован в небытие."
        )

    # Extension-specific sarcasm
    ext = metrics.dominant_extension
    if ext in (".exe", ".dll", ".bin"):
        return (
            f"[SHREDDER] Скомпилированный бинарник ({ext}) переварен. "
            "Исполняемый код аннигилирован."
        )
    if ext in (".log", ".tmp", ".bak", ".dump"):
        return (
            f"[SHREDDER] Цифровой мусор ({ext}) стерт. "
            "Корзины тебе уже мало, носишь хлам прямо мне?"
        )
    if ext in (".py", ".js", ".cpp", ".rs", ".java", ".html", ".css", ".ts"):
        return (
            f"[SHREDDER] Исходный код ({ext}) поглощен. "
            "Надеюсь, в репозитории был коммит."
        )
    if ext in (".zip", ".rar", ".7z", ".tar", ".gz"):
        return (
            f"[SHREDDER] Архив {metrics.sample_name} распакован прямо в вакуум."
        )

    if metrics.total_dirs > 0:
        return (
            f"[SHREDDER] Директория '{metrics.sample_name}' и всё её содержимое ({metrics.total_files} файлов) "
            "навсегда стерты из файловой системы."
        )

    return (
        f"[SHREDDER] Объект '{metrics.sample_name}' ({size_mb:.1f} МБ) дезинтегрирован."
    )
