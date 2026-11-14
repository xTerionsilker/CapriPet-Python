"""Безопасная очистка временных файлов и корзины в операционной системе Windows.

Модуль предоставляет средства для очистки системных и пользовательских
временных каталогов (Temp), освобождения корзины Windows через Shell API
и форматирования объема высвобожденного дискового пространства.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from pathlib import Path
from typing import NamedTuple

import humanize
from win32com.shell import shell, shellcon

logger = logging.getLogger(__name__)


class CleanResult(NamedTuple):
    """Результат выполнения операции системной очистки.

    Attributes:
        files_deleted: Общее количество успешно удаленных файлов и элементов.
        bytes_freed: Суммарный объем освобожденного места на диске в байтах.
        errors: Число файлов или каталогов, пропущенных из-за ошибок доступа.
        recycle_bin_cleared: Флаг успешной очистки системной корзины.
    """

    files_deleted: int
    bytes_freed: int
    errors: int
    recycle_bin_cleared: bool


def format_bytes(bytes_count: float) -> str:
    """Форматирует байты в удобную читаемую строку с помощью humanize."""
    return humanize.naturalsize(max(0.0, float(bytes_count)), binary=True)


def clear_recycle_bin() -> tuple[bool, int, int]:
    """Безопасно очищает корзину Windows через Shell API.

    Возвращает:
        (успех, количество_элементов, байт_освобождено)
    """
    try:
        size, count = shell.SHQueryRecycleBin(None)
        num_items = int(count)
        bytes_size = max(0, int(size))
        if num_items <= 0:
            return True, 0, 0

        flags = (
            shellcon.SHERB_NOCONFIRMATION
            | shellcon.SHERB_NOPROGRESSUI
            | shellcon.SHERB_NOSOUND
        )
        shell.SHEmptyRecycleBin(None, None, flags)
        return True, num_items, bytes_size
    except Exception as exc:
        logger.debug("Ошибка при очистке корзины через Shell API: %s", exc)
        return False, 0, 0


def _is_strictly_within(
    target_path: str | Path, base_dir: str | Path
) -> bool:
    """Проверяет, что target_path находится строго внутри base_dir и не выходит за его пределы."""
    try:
        target_res = Path(target_path).resolve()
        base_res = Path(base_dir).resolve()
        return target_res.is_relative_to(base_res) and target_res != base_res
    except (OSError, ValueError):
        return False


def _safe_remove_file(
    file_path: str, base_dir: str | None = None
) -> tuple[bool, int]:
    try:
        if base_dir and not _is_strictly_within(file_path, base_dir):
            return False, 0
        if os.path.islink(file_path):
            os.unlink(file_path)
            return True, 0
        size = 0
        with contextlib.suppress(OSError):
            size = os.path.getsize(file_path)
        os.remove(file_path)
        return True, size
    except OSError:
        return False, 0


def _safe_remove_dir(
    dir_path: str, base_dir: str | None = None
) -> tuple[int, int, int]:
    """Рекурсивно удаляет содержимое папки снизу вверх, пропуская заблокированные файлы."""
    files_del = 0
    bytes_del = 0
    err_count = 0

    if base_dir and not _is_strictly_within(dir_path, base_dir):
        return 0, 0, 1

    if os.path.islink(dir_path):
        try:
            os.unlink(dir_path)
            return 1, 0, 0
        except OSError:
            return 0, 0, 1

    for root, dirs, files in os.walk(dir_path, topdown=False, followlinks=False):
        for f in files:
            fp = os.path.join(root, f)
            ok, sz = _safe_remove_file(fp, base_dir=base_dir)
            if ok:
                files_del += 1
                bytes_del += sz
            else:
                err_count += 1
        for d in dirs:
            dp = os.path.join(root, d)
            if os.path.islink(dp):
                try:
                    os.unlink(dp)
                    files_del += 1
                except OSError:
                    err_count += 1
            else:
                with contextlib.suppress(OSError):
                    os.rmdir(dp)

    with contextlib.suppress(OSError):
        os.rmdir(dir_path)

    return files_del, bytes_del, err_count


def clean_temp_directories() -> tuple[int, int, int]:
    """Безопасно очищает содержимое только временных директорий пользователя и Windows.

    Пропускает любые файлы, заблокированные системой или другими приложениями.
    Сами папки Temp не удаляются.
    """
    total_files = 0
    total_bytes = 0
    total_errors = 0

    target_dirs: list[str] = []

    user_temp = tempfile.gettempdir()
    if user_temp and os.path.isdir(user_temp):
        target_dirs.append(user_temp)

    win_dir = os.environ.get("WINDIR", r"C:\Windows")
    sys_temp = os.path.join(win_dir, "Temp")
    if os.path.isdir(sys_temp) and sys_temp.lower() != user_temp.lower():
        target_dirs.append(sys_temp)

    for temp_dir in target_dirs:
        try:
            with os.scandir(temp_dir) as entries:
                items = list(entries)
        except OSError:
            continue

        for item in items:
            try:
                if not _is_strictly_within(item.path, temp_dir):
                    total_errors += 1
                    continue

                if (
                    item.is_file(follow_symlinks=False)
                    or item.is_symlink()
                ):
                    ok, sz = _safe_remove_file(item.path, base_dir=temp_dir)
                    if ok:
                        total_files += 1
                        total_bytes += sz
                    else:
                        total_errors += 1
                elif item.is_dir(follow_symlinks=False):
                    f_del, b_del, errs = _safe_remove_dir(
                        item.path, base_dir=temp_dir
                    )
                    total_files += f_del
                    total_bytes += b_del
                    total_errors += errs
            except OSError:
                total_errors += 1

    return total_files, total_bytes, total_errors


def perform_system_cleanup() -> CleanResult:
    """Выполняет полную безопасную очистку временных файлов и корзины."""
    # 1. Корзина
    rb_cleared, rb_items, rb_bytes = clear_recycle_bin()

    # 2. Временные файлы
    temp_files, temp_bytes, errors = clean_temp_directories()

    total_files = rb_items + temp_files
    total_bytes = rb_bytes + temp_bytes

    return CleanResult(
        files_deleted=total_files,
        bytes_freed=total_bytes,
        errors=errors,
        recycle_bin_cleared=rb_cleared,
    )
