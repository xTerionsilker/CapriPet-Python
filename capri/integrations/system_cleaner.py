"""Безопасная очистка временных файлов и корзины в операционной системе Windows.

Модуль предоставляет средства для очистки системных и пользовательских
временных каталогов (Temp), освобождения корзины Windows через Shell API
и форматирования объема высвобожденного дискового пространства.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import tempfile
from ctypes import wintypes
from typing import Any, NamedTuple


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


class _SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("i64Size", ctypes.c_int64),
        ("i64NumItems", ctypes.c_int64),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cbSize = ctypes.sizeof(self)


SHERB_NOCONFIRMATION = 0x00000001
SHERB_NOPROGRESSUI = 0x00000002
SHERB_NOSOUND = 0x00000004


def format_bytes(bytes_count: int | float) -> str:
    """Форматирует байты в удобную читаемую строку."""
    b = float(max(0, bytes_count))
    if b < 1024:
        return f"{int(b)} Б"
    for unit in ("КБ", "МБ", "ГБ", "ТБ"):
        b /= 1024.0
        if b < 1024.0:
            return f"{b:.1f} {unit}"
    return f"{b:.1f} ПБ"


def clear_recycle_bin() -> tuple[bool, int, int]:
    """Безопасно очищает корзину Windows через Shell API.

    Возвращает:
        (успех, количество_элементов, байт_освобождено)
    """
    try:
        info = _SHQUERYRBINFO()
        hr = ctypes.windll.shell32.SHQueryRecycleBinW(
            None, ctypes.byref(info)
        )
        if hr != 0:
            return False, 0, 0

        num_items = int(info.i64NumItems)
        bytes_size = int(info.i64Size)

        if num_items <= 0:
            return True, 0, 0

        flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        # S_OK = 0
        if res == 0:
            return True, num_items, max(0, bytes_size)
    except Exception:
        pass
    return False, 0, 0


def _safe_remove_file(file_path: str) -> tuple[bool, int]:
    try:
        size = 0
        with contextlib.suppress(OSError):
            size = os.path.getsize(file_path)
        os.remove(file_path)
        return True, size
    except OSError:
        return False, 0


def _safe_remove_dir(dir_path: str) -> tuple[int, int, int]:
    """Рекурсивно удаляет содержимое папки снизу вверх, пропуская заблокированные файлы."""
    files_del = 0
    bytes_del = 0
    err_count = 0

    for root, dirs, files in os.walk(dir_path, topdown=False):
        for f in files:
            fp = os.path.join(root, f)
            ok, sz = _safe_remove_file(fp)
            if ok:
                files_del += 1
                bytes_del += sz
            else:
                err_count += 1
        for d in dirs:
            dp = os.path.join(root, d)
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
                if (
                    item.is_file(follow_symlinks=False)
                    or item.is_symlink()
                ):
                    ok, sz = _safe_remove_file(item.path)
                    if ok:
                        total_files += 1
                        total_bytes += sz
                    else:
                        total_errors += 1
                elif item.is_dir(follow_symlinks=False):
                    f_del, b_del, errs = _safe_remove_dir(item.path)
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
