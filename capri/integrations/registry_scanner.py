"""Диагностика и сканирование реестра Windows на пустые и повреждённые ключи.

Модуль выполняет безопасное (только чтение) сканирование реестра Windows для
обнаружения пустых веток деинсталлированного софта, битых записей автозапуска,
повреждённых путей деинсталляторов и недействительных путей App Paths.
Результаты сохраняются в текстовый отчет в каталоге TEMP и открываются пользователю.
"""

from __future__ import annotations

import datetime
import os
import re
import tempfile
import winreg
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RegistryIssue:
    """Обнаруженная проблема в системном реестре."""

    category: str
    hive_name: str
    key_path: str
    details: str


@dataclass(frozen=True)
class ScanReport:
    """Итоговый отчет сканирования реестра."""

    issues: list[RegistryIssue]
    total_scanned: int
    report_path: Path


# Известные системные ветки, которые допустимо оставлять пустыми в ОС
_IGNORED_EMPTY_KEYS: frozenset[str] = frozenset(
    {
        "classes",
        "policies",
        "microsoft",
        "registeredapplications",
        "wow6432node",
        "clients",
    }
)


def extract_executable_path(command_line: str) -> str | None:
    """Извлекает путь к исполняемому файлу из строки запуска или аргументов."""
    if not command_line or not command_line.strip():
        return None

    cmd = os.path.expandvars(command_line.strip())

    # 1. Если путь обрамлен в кавычки
    if cmd.startswith('"'):
        end_idx = cmd.find('"', 1)
        if end_idx != -1:
            return cmd[1:end_idx].strip()
        return cmd.strip('"').strip()

    # 2. Попытка выделить путь до первого разделителя аргументов
    # Проверяем, существует ли полный путь или префиксы с расширениями
    match = re.match(r"^([a-zA-Z]:\\[^/:*?\"<>|\r\n]+?\.(?:exe|bat|cmd|vbs|dll))(?:\s|$)", cmd, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Если пробелы в пути без кавычек, пробуем жадное совпадение
    parts = cmd.split()
    accumulated = ""
    for part in parts:
        accumulated = f"{accumulated} {part}".strip() if accumulated else part
        if os.path.isfile(accumulated):
            return accumulated

    # Первое слово по умолчанию
    first_token = parts[0]
    if ":\\" in first_token or first_token.startswith("\\"):
        return first_token

    return None


def _is_file_missing(file_path: str | None) -> bool:
    """Проверяет, указывает ли путь на гарантированно отсутствующий локальный файл."""
    if not file_path:
        return False
    # Игнорируем псевдо-команды типа msiexec, rundll32, regsvr32 без абсолютных путей
    if not (":\\" in file_path or file_path.startswith("\\\\")):
        return False
    try:
        return not Path(file_path).exists()
    except (OSError, ValueError):
        return True


def scan_empty_software_keys() -> tuple[list[RegistryIssue], int]:
    """Сканирует разделы Software на пустые ветки (0 подключей и 0 параметров)."""
    issues: list[RegistryIssue] = []
    scanned = 0

    targets = [
        (winreg.HKEY_CURRENT_USER, "HKCU", r"Software"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\WOW6432Node"),
    ]

    for root_hive, hive_name, root_path in targets:
        try:
            with winreg.OpenKey(root_hive, root_path, 0, winreg.KEY_READ) as root_key:
                num_subkeys, _, _ = winreg.QueryInfoKey(root_key)
                for i in range(num_subkeys):
                    scanned += 1
                    try:
                        vendor_name = winreg.EnumKey(root_key, i)
                    except OSError:
                        continue

                    if vendor_name.lower() in _IGNORED_EMPTY_KEYS:
                        continue

                    vendor_subpath = f"{root_path}\\{vendor_name}"
                    try:
                        with winreg.OpenKey(root_hive, vendor_subpath, 0, winreg.KEY_READ) as vendor_key:
                            v_subkeys, v_values, _ = winreg.QueryInfoKey(vendor_key)
                            # Если сама ветка вендора пуста
                            if v_subkeys == 0 and v_values == 0:
                                issues.append(
                                    RegistryIssue(
                                        category="Пустой раздел (мусор ПО)",
                                        hive_name=hive_name,
                                        key_path=vendor_subpath,
                                        details="Раздел не содержит параметров и подключей (остаток деинсталляции).",
                                    )
                                )
                                continue

                            # Проверяем вложенные программы вендора (уровень 2)
                            for j in range(v_subkeys):
                                scanned += 1
                                try:
                                    app_name = winreg.EnumKey(vendor_key, j)
                                    app_subpath = f"{vendor_subpath}\\{app_name}"
                                    with winreg.OpenKey(root_hive, app_subpath, 0, winreg.KEY_READ) as app_key:
                                        a_subkeys, a_values, _ = winreg.QueryInfoKey(app_key)
                                        if a_subkeys == 0 and a_values == 0:
                                            issues.append(
                                                RegistryIssue(
                                                    category="Пустой раздел (мусор ПО)",
                                                    hive_name=hive_name,
                                                    key_path=app_subpath,
                                                    details="Подраздел приложения пуст (остаток после удаления программы).",
                                                )
                                            )
                                except OSError:
                                    continue
                    except OSError:
                        continue
        except OSError:
            continue

    return issues, scanned


def scan_broken_uninstallers() -> tuple[list[RegistryIssue], int]:
    """Сканирует ветки деинсталляции на записи с отсутствующими исполняемыми файлами."""
    issues: list[RegistryIssue] = []
    scanned = 0

    uninstall_paths = [
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, "HKCU", r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for root_hive, hive_name, root_path in uninstall_paths:
        try:
            with winreg.OpenKey(root_hive, root_path, 0, winreg.KEY_READ) as u_key:
                num_subkeys, _, _ = winreg.QueryInfoKey(u_key)
                for i in range(num_subkeys):
                    scanned += 1
                    try:
                        sub_name = winreg.EnumKey(u_key, i)
                        sub_path = f"{root_path}\\{sub_name}"
                        with winreg.OpenKey(root_hive, sub_path, 0, winreg.KEY_READ) as item_key:
                            # Проверяем UninstallString
                            uninstall_str = ""
                            try:
                                val, _ = winreg.QueryValueEx(item_key, "UninstallString")
                                uninstall_str = str(val) if val else ""
                            except OSError:
                                pass

                            if uninstall_str:
                                exe = extract_executable_path(uninstall_str)
                                if exe and _is_file_missing(exe):
                                    issues.append(
                                        RegistryIssue(
                                            category="Битая деинсталляция",
                                            hive_name=hive_name,
                                            key_path=sub_path,
                                            details=f"Файл деинсталлятора отсутствует: {exe}",
                                        )
                                    )
                                    continue

                            # Проверяем InstallLocation, если указан
                            try:
                                loc, _ = winreg.QueryValueEx(item_key, "InstallLocation")
                                loc_str = str(loc).strip().strip('"') if loc else ""
                                if loc_str and ":\\" in loc_str and not Path(loc_str).exists():
                                    issues.append(
                                        RegistryIssue(
                                            category="Несуществующая папка установки",
                                            hive_name=hive_name,
                                            key_path=sub_path,
                                            details=f"Каталог установки не найден: {loc_str}",
                                        )
                                    )
                            except OSError:
                                pass
                    except OSError:
                        continue
        except OSError:
            continue

    return issues, scanned


def scan_broken_startup_entries() -> tuple[list[RegistryIssue], int]:
    """Сканирует параметры автозапуска (Run/RunOnce) на битые ссылки."""
    issues: list[RegistryIssue] = []
    scanned = 0

    run_paths = [
        (winreg.HKEY_CURRENT_USER, "HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_CURRENT_USER, "HKCU", r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
    ]

    for root_hive, hive_name, path in run_paths:
        try:
            with winreg.OpenKey(root_hive, path, 0, winreg.KEY_READ) as key:
                _, num_values, _ = winreg.QueryInfoKey(key)
                for i in range(num_values):
                    scanned += 1
                    try:
                        val_name, val_data, _ = winreg.EnumValue(key, i)
                        if isinstance(val_data, str) and val_data.strip():
                            exe = extract_executable_path(val_data)
                            if exe and _is_file_missing(exe):
                                issues.append(
                                    RegistryIssue(
                                        category="Битая автозагрузка",
                                        hive_name=hive_name,
                                        key_path=f"{path} -> [{val_name}]",
                                        details=f"Исполняемый файл не найден: {exe}",
                                    )
                                )
                    except OSError:
                        continue
        except OSError:
            continue

    return issues, scanned


def scan_broken_app_paths() -> tuple[list[RegistryIssue], int]:
    """Сканирует App Paths на несуществующие файлы приложений."""
    issues: list[RegistryIssue] = []
    scanned = 0

    targets = [
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, "HKCU", r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
    ]

    for root_hive, hive_name, path in targets:
        try:
            with winreg.OpenKey(root_hive, path, 0, winreg.KEY_READ) as key:
                num_subkeys, _, _ = winreg.QueryInfoKey(key)
                for i in range(num_subkeys):
                    scanned += 1
                    try:
                        sub_name = winreg.EnumKey(key, i)
                        sub_path = f"{path}\\{sub_name}"
                        with winreg.OpenKey(root_hive, sub_path, 0, winreg.KEY_READ) as app_key:
                            try:
                                default_val, _ = winreg.QueryValueEx(app_key, "")
                                if isinstance(default_val, str) and default_val.strip():
                                    exe = extract_executable_path(default_val)
                                    if exe and _is_file_missing(exe):
                                        issues.append(
                                            RegistryIssue(
                                                category="Битой App Path",
                                                hive_name=hive_name,
                                                key_path=sub_path,
                                                details=f"Целевой бинарник не найден: {exe}",
                                            )
                                        )
                            except OSError:
                                pass
                    except OSError:
                        continue
        except OSError:
            continue

    return issues, scanned


def generate_report_file(issues: list[RegistryIssue], total_scanned: int) -> Path:
    """Формирует текстовый файл отчета в каталоге TEMP."""
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = Path(tempfile.gettempdir())
    report_file = temp_dir / f"capri_registry_scan_{timestamp_str}.txt"

    lines: list[str] = [
        "================================================================================",
        "             CAPRI BLACKWALL REGISTRY DIAGNOSTIC REPORT                         ",
        "================================================================================",
        f"Дата и время сканирования: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Всего проверено записей:  {total_scanned}",
        f"Обнаружено аномалий:      {len(issues)}",
        "Режим:                    Только чтение (безопасный аудит)",
        "--------------------------------------------------------------------------------",
        "",
    ]

    if not issues:
        lines.extend([
            "[+] Аномалий не обнаружено. Реестр чист, мертвых хвостов ПО не зафиксировано.",
            "",
        ])
    else:
        # Группировка по категориям
        grouped: dict[str, list[RegistryIssue]] = {}
        for issue in issues:
            grouped.setdefault(issue.category, []).append(issue)

        for cat, cat_issues in grouped.items():
            lines.append(f"=== {cat.upper()} ({len(cat_issues)}) ===")
            for item in cat_issues:
                lines.append(f"[{item.hive_name}] {item.key_path}")
                lines.append(f"    Причина: {item.details}")
            lines.append("")

    lines.extend([
        "--------------------------------------------------------------------------------",
        "Диагностика сгенерирована ядром CapriPet. Никаких изменений в реестр внесено не было.",
        "================================================================================",
    ])

    report_file.write_text("\n".join(lines), encoding="utf-8")
    return report_file


def perform_registry_scan(open_report: bool = True) -> ScanReport:
    """Выполняет полный аудит реестра, сохраняет отчет и открывает его."""
    all_issues: list[RegistryIssue] = []
    total_scanned = 0

    # 1. Пустые ветки ПО
    empty_issues, count1 = scan_empty_software_keys()
    all_issues.extend(empty_issues)
    total_scanned += count1

    # 2. Битые записи деинсталляторов
    uninst_issues, count2 = scan_broken_uninstallers()
    all_issues.extend(uninst_issues)
    total_scanned += count2

    # 3. Битые ссылки автозагрузки
    startup_issues, count3 = scan_broken_startup_entries()
    all_issues.extend(startup_issues)
    total_scanned += count3

    # 4. Битые пути App Paths
    apppath_issues, count4 = scan_broken_app_paths()
    all_issues.extend(apppath_issues)
    total_scanned += count4

    # Генерация отчета
    report_path = generate_report_file(all_issues, total_scanned)

    # Открытие файла через системную ассоциацию
    if open_report:
        try:
            os.startfile(str(report_path))
        except OSError:
            pass

    return ScanReport(
        issues=all_issues,
        total_scanned=total_scanned,
        report_path=report_path,
    )
