"""Unit tests for the Windows Registry diagnostic scanner integration and command."""

from __future__ import annotations

import unittest

from capri.commands import create_default_registry
from capri.commands.base import CommandContext
from capri.commands.handlers import RegistryCommand
from capri.integrations.registry_scanner import (
    RegistryIssue,
    extract_executable_path,
    generate_report_file,
    perform_registry_scan,
)


class TestRegistryScanner(unittest.TestCase):
    """Тестирование сканера реестра и команды реестра."""

    def test_extract_executable_path_quoted(self) -> None:
        raw = '"C:\\Program Files\\App\\target.exe" /silent /norestart'
        extracted = extract_executable_path(raw)
        self.assertEqual(extracted, "C:\\Program Files\\App\\target.exe")

    def test_extract_executable_path_unquoted(self) -> None:
        raw = "C:\\Windows\\System32\\cmd.exe /c dir"
        extracted = extract_executable_path(raw)
        self.assertEqual(extracted, "C:\\Windows\\System32\\cmd.exe")

    def test_extract_executable_path_empty(self) -> None:
        self.assertIsNone(extract_executable_path(""))
        self.assertIsNone(extract_executable_path("   "))

    def test_generate_report_file(self) -> None:
        issues = [
            RegistryIssue(
                category="Пустой раздел (мусор ПО)",
                hive_name="HKCU",
                key_path=r"Software\TestVendor\OldApp",
                details="0 ключей и 0 параметров",
            ),
            RegistryIssue(
                category="Битая деинсталляция",
                hive_name="HKLM",
                key_path=r"Software\Microsoft\Windows\CurrentVersion\Uninstall\GhostApp",
                details="Файл не найден",
            ),
        ]

        report_path = generate_report_file(issues, total_scanned=42)
        try:
            self.assertTrue(report_path.exists())
            self.assertTrue(report_path.is_file())
            content = report_path.read_text(encoding="utf-8")
            self.assertIn("CAPRI BLACKWALL REGISTRY DIAGNOSTIC REPORT", content)
            self.assertIn("Всего проверено записей:  42", content)
            self.assertIn("Обнаружено аномалий:      2", content)
            self.assertIn(r"Software\TestVendor\OldApp", content)
            self.assertIn("GhostApp", content)
        finally:
            if report_path.exists():
                report_path.unlink()

    def test_perform_registry_scan_live(self) -> None:
        report = perform_registry_scan(open_report=False)
        self.assertGreater(report.total_scanned, 0)
        self.assertTrue(report.report_path.exists())
        try:
            content = report.report_path.read_text(encoding="utf-8")
            self.assertIn("CAPRI BLACKWALL REGISTRY DIAGNOSTIC REPORT", content)
        finally:
            if report.report_path.exists():
                report.report_path.unlink()

    def test_registry_command_in_default_registry(self) -> None:
        registry = create_default_registry()
        matched = registry.find("реестр")
        self.assertIsNotNone(matched)
        self.assertIsInstance(matched, RegistryCommand)

        matched_alias = registry.find("сканировать реестр")
        self.assertIsNotNone(matched_alias)
        self.assertIsInstance(matched_alias, RegistryCommand)

        matched_en = registry.find("registry")
        self.assertIsNotNone(matched_en)
        self.assertIsInstance(matched_en, RegistryCommand)

    def test_registry_command_execute_direct(self) -> None:
        cmd = RegistryCommand()
        ctx = CommandContext(
            speak=lambda msg: None,
            trigger_glitches=lambda: "",
            toggle_voice=lambda: "",
            locate_mouse=lambda: "",
            set_pose=lambda pose: None,
            get_config=lambda k, d: d,
            set_config=lambda k, v: None,
            action_bridge=None,
        )
        result = cmd.execute(ctx)
        self.assertIsNotNone(result)
        self.assertTrue(
            ("Прошерстила" in result) or ("Анализ реестра завершён" in result)
        )


if __name__ == "__main__":
    unittest.main()
