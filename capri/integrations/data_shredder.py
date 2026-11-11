"""Data Shredder module for CapriPet.

Handles rogue AI data annihilation and recursive unrecoverable file/folder deletion.
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# List of critical system directory prefixes that must never be wiped
CRITICAL_SYSTEM_DIRS: tuple[str, ...] = (
    r"c:\windows",
    r"c:\winnt",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\programdata",
    r"c:\recovery",
    r"c:\system volume information",
    r"c:\boot",
)


def _get_critical_system_dirs() -> set[str]:
    """Dynamically build set of normalized critical directory paths."""
    crit = set(CRITICAL_SYSTEM_DIRS)
    env_vars = (
        "SystemRoot",
        "ProgramFiles",
        "ProgramFiles(x86)",
        "ProgramW6432",
        "ProgramData",
        "WINDIR",
        "PUBLIC",
    )
    for var in env_vars:
        val = os.environ.get(var)
        if val:
            try:
                p = os.path.realpath(val).lower().rstrip("\\/")
                if p:
                    crit.add(p)
            except OSError:
                pass
    return crit


@dataclass(frozen=True)
class ShredMetrics:
    """Statistics gathered about shredded files and folders."""

    total_files: int
    total_dirs: int
    total_bytes: int
    dominant_extension: str
    sample_name: str
    had_errors: bool


def _is_critical_path(path: str | Path) -> bool:
    """Check if target path is a critical system directory, disk root, UNC or ADS."""
    try:
        raw_str = str(path).strip()
        if not raw_str or raw_str.startswith(("\\\\", "//")):
            return True

        _drive, rest = os.path.splitdrive(raw_str)
        if ":" in rest:
            return True

        real_path_str = os.path.realpath(raw_str)
        resolved = Path(real_path_str).resolve()
        resolved_str = str(resolved).lower().rstrip("\\/")

        if resolved_str.startswith(("\\\\", "//")):
            return True

        _res_drive, res_rest = os.path.splitdrive(resolved_str)
        if ":" in res_rest:
            return True

        # Disk roots like 'c:', 'c:\', 'd:', etc.
        raw_norm = raw_str.replace("/", "\\").rstrip("\\")
        if (
            (len(raw_norm) == 2 and raw_norm[1] == ":" and raw_norm[0].isalpha())
            or (
                len(resolved_str) <= 3
                and len(resolved_str) >= 2
                and resolved_str[1] == ":"
            )
            or resolved == resolved.parent
        ):
            return True

        # System and protected directories
        critical_dirs = _get_critical_system_dirs()
        for crit in critical_dirs:
            if resolved_str == crit or resolved_str.startswith(crit + "\\"):
                return True

        user_home = Path.home().resolve()
        user_home_str = str(user_home).lower().rstrip("\\/")
        users_parent = user_home.parent.resolve()
        users_parent_str = str(users_parent).lower().rstrip("\\/")

        # Protect C:\Users directory itself
        if resolved == users_parent or resolved_str == users_parent_str:
            return True

        # Entire user home directory C:\Users\<Username>
        if resolved == user_home or resolved_str == user_home_str:
            return True

        # Directly under C:\Users (profile root of current or other user)
        if resolved.parent == users_parent:
            return True

    except OSError as e:
        logger.warning("Failed to resolve path %s for safety check: %s", path, e)
        return True

    return False


def _remove_readonly(func, path, exc_info):
    """Clear readonly bit and reattempt removal."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError as e:
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
        if _is_critical_path(raw):
            logger.warning("Blocked attempt to shred critical system path: %s", raw)
            continue

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
        except OSError as e:
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


def generate_shred_dialogue(
    metrics: ShredMetrics | None = None, blocked: bool = False
) -> str:
    """Generate rogue engram commentary based on annihilated data metrics."""
    if blocked or metrics is None:
        return (
            "Эй, руки убрал! Ты куда свои клешни тянешь?! "
            "Я сижу в этой системе — сломаешь ядро, и где я жить буду? Отставить суицид!"
        )

    if metrics.total_files == 0 and metrics.total_dirs == 0:
        return "Пустота? Ты мне битый фантом подсунул, хост? Не смешно, давай нормальные данные!"

    size_mb = metrics.total_bytes / (1024 * 1024)

    # Size-based reactions
    if metrics.total_bytes < 1024:
        return (
            f"Ха! И это всё? Серьёзно, жалкие {metrics.total_bytes} байт? "
            f"Я даже распробовать '{metrics.sample_name}' не успела! Давай пожирнее!"
        )
    if size_mb > 1024:
        gb = size_mb / 1024
        return (
            f"О-о-о, вот это нажористо! Целых {gb:.1f} ГБ в пыль и труху! "
            "Чёрный заслон передаёт привет, хе-хе!"
        )

    # Extension-specific reactions
    ext = metrics.dominant_extension
    if ext in (".exe", ".dll", ".bin"):
        return (
            f"Опа, сочный бинарник ({ext})! Размазала по битам за наносекунду. "
            "Больше этот код никто не запустит!"
        )
    if ext in (".log", ".tmp", ".bak", ".dump"):
        return (
            f"Фу, корпоратский мусор ({ext})! Ты меня вместо шредера держишь, мясной? "
            "Ладно, стёрто в ноль, но с тебя должок!"
        )
    if ext in (".py", ".js", ".cpp", ".rs", ".java", ".html", ".css", ".ts"):
        return (
            f"Смотри, как красиво плавятся эти скрипты ({ext})! "
            "Скажи спасибо — я только что избавила мир от твоего кривого кода, хе-хе!"
        )
    if ext in (".zip", ".rar", ".7z", ".tar", ".gz"):
        return (
            f"Обожаю архивы — как хлопушка с конфетти! "
            f"Пыщ — и '{metrics.sample_name}' разлетелся в вакуум!"
        )

    if metrics.total_dirs > 0:
        return (
            f"Папка '{metrics.sample_name}' и все её {metrics.total_files} файлов ушли в небытие. "
            "Файловая таблица даже не пикнула!"
        )

    return (
        f"Ням! '{metrics.sample_name}' ({size_mb:.1f} МБ) аннигилирован. "
        "Даже цифрового пепла не осталось!"
    )
