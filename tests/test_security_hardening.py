"""Автоматизированные тесты комплексного аудита безопасности и харденинга (Issue #20)."""

from __future__ import annotations

import contextlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from capri.commands.registry import MAX_COMMAND_INPUT_LENGTH, CommandRegistry
from capri.core.input_flow import (
    MAX_INPUT_TEXT_LENGTH,
    InputFlow,
    answer_words,
)
from capri.core.settings import (
    DEFAULT_CONFIG,
    MAX_CONFIG_FILE_SIZE,
    ConfigManager,
)
from capri.integrations.app_launcher import (
    BLOCKED_SCRIPT_EXTENSIONS,
    is_safe_executable_path,
    launch_application,
)
from capri.integrations.data_shredder import (
    ShredMetrics,
    _is_critical_path,
    generate_shred_dialogue,
)
from capri.integrations.system_cleaner import (
    _is_strictly_within,
    _safe_remove_dir,
    _safe_remove_file,
)
from capri.integrations.web_search import safe_open_url


class TestDataShredderSecurity(unittest.TestCase):
    """Тестирование защиты DataShredder от разрушения системных каталогов и обхода путей."""

    def test_blocks_windows_system_directories(self) -> None:
        self.assertTrue(_is_critical_path(r"C:\Windows"))
        self.assertTrue(_is_critical_path(r"C:\Windows\System32"))
        self.assertTrue(_is_critical_path(r"C:\Program Files"))
        self.assertTrue(_is_critical_path(r"C:\Program Files (x86)"))
        self.assertTrue(_is_critical_path(r"C:\ProgramData"))

    def test_blocks_disk_roots(self) -> None:
        self.assertTrue(_is_critical_path(r"C:\\"))
        self.assertTrue(_is_critical_path(r"C:"))
        self.assertTrue(_is_critical_path(r"D:\\"))
        self.assertTrue(_is_critical_path(r"d:"))

    def test_blocks_unc_paths(self) -> None:
        self.assertTrue(_is_critical_path(r"\\192.168.1.1\c$\Windows"))
        self.assertTrue(_is_critical_path(r"\\nas\storage"))
        self.assertTrue(_is_critical_path(r"//nas/storage"))

    def test_blocks_ntfs_alternate_data_streams(self) -> None:
        self.assertTrue(_is_critical_path(r"C:\safe_folder\test.txt:hidden"))
        self.assertTrue(_is_critical_path(r"C:\test.txt:ADS:$DATA"))

    def test_blocks_user_profile_roots(self) -> None:
        self.assertTrue(_is_critical_path(Path.home()))
        users_parent = Path.home().parent
        other_user = users_parent / "OtherPerson"
        self.assertTrue(_is_critical_path(other_user))
        self.assertTrue(_is_critical_path(users_parent))

    def test_allows_safe_temp_file(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = Path(f.name)
        try:
            self.assertFalse(_is_critical_path(temp_path))
        finally:
            temp_path.unlink(missing_ok=True)

    def test_blocked_dialogue_generation(self) -> None:
        dialogue = generate_shred_dialogue(None, blocked=True)
        self.assertIn("руки убрал", dialogue)
        metrics = ShredMetrics(0, 0, 0, "", "", False)
        dialogue2 = generate_shred_dialogue(metrics, blocked=True)
        self.assertIn("Отставить суицид", dialogue2)


class TestSystemCleanerSecurity(unittest.TestCase):
    """Тестирование локализации очистки временных файлов и защиты от выхода за границы."""

    def test_is_strictly_within(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            subfile = Path(base) / "test.tmp"
            subfile.touch()
            subdir = Path(base) / "subdir"
            subdir.mkdir()
            nested = subdir / "nested.tmp"
            nested.touch()

            self.assertTrue(_is_strictly_within(subfile, base))
            self.assertTrue(_is_strictly_within(subdir, base))
            self.assertTrue(_is_strictly_within(nested, base))

            # Сам каталог не должен считаться строго внутри самого себя
            self.assertFalse(_is_strictly_within(base, base))

            # Попытка выхода через ..
            escape = Path(base) / ".." / "other.tmp"
            self.assertFalse(_is_strictly_within(escape, base))

    def test_safe_remove_file_outside_base_dir_fails(self) -> None:
        with (
            tempfile.TemporaryDirectory() as base,
            tempfile.NamedTemporaryFile(delete=False) as outside,
        ):
            outside_path = outside.name

        try:
            ok, _ = _safe_remove_file(outside_path, base_dir=base)
            self.assertFalse(ok)
            self.assertTrue(os.path.exists(outside_path))
        finally:
            with contextlib.suppress(OSError):
                os.remove(outside_path)

    def test_safe_remove_dir_outside_base_dir_fails(self) -> None:
        with (
            tempfile.TemporaryDirectory() as base,
            tempfile.TemporaryDirectory() as outside,
        ):
            f, _b, errs = _safe_remove_dir(outside, base_dir=base)
            self.assertEqual(f, 0)
            self.assertEqual(errs, 1)
            self.assertTrue(os.path.exists(outside))


class TestAppLauncherSecurity(unittest.TestCase):
    """Тестирование валидации исполняемых файлов и блокировки скриптовых расширений."""

    def test_blocks_dangerous_extensions(self) -> None:
        for ext in BLOCKED_SCRIPT_EXTENSIONS:
            fake_script = f"C:\\Windows\\Temp\\exploit{ext}"
            self.assertFalse(
                is_safe_executable_path(fake_script),
                f"Расширение {ext} должно быть заблокировано!",
            )

    def test_blocks_nonexistent_exe(self) -> None:
        self.assertFalse(is_safe_executable_path(r"C:\NonExistent_App_123.exe"))

    def test_launch_application_returns_false_for_malicious_app(self) -> None:
        malicious_apps = [
            {"name": "Evil", "exec": r"C:\Windows\System32\cmd.exe /c calc.bat"},
            {"name": "BadScript", "exec": r"C:\Temp\payload.ps1"},
            {"name": "Missing", "exec": r"C:\Temp\fake.exe"},
            {"name": "Empty", "exec": ""},
        ]
        for app in malicious_apps:
            self.assertFalse(launch_application(app))


class TestWebSearchSecurity(unittest.TestCase):
    """Тестирование вайтлистинга URL схем и защиты от кастомных системных протоколов."""

    def test_blocks_dangerous_schemes(self) -> None:
        with patch("capri.integrations.web_search.webbrowser.open") as mock_open:
            self.assertFalse(safe_open_url("file:///C:/Windows/System32/cmd.exe"))
            self.assertFalse(safe_open_url("ms-msdt:/id PCWDiagnostic"))
            self.assertFalse(safe_open_url("calculator:"))
            self.assertFalse(safe_open_url("javascript:alert(1)"))
            self.assertFalse(safe_open_url(""))
            self.assertFalse(safe_open_url("   "))
            self.assertFalse(safe_open_url("https://"))  # Без хоста
            mock_open.assert_not_called()

    def test_allows_valid_https_url(self) -> None:
        with patch(
            "capri.integrations.web_search.webbrowser.open", return_value=True
        ) as mock_open:
            ok = safe_open_url("https://www.google.com/search?q=test")
            self.assertTrue(ok)
            mock_open.assert_called_once_with("https://www.google.com/search?q=test")


class TestConfigSecurity(unittest.TestCase):
    """Тестирование защиты ConfigManager от переполнения и некорректных путей."""

    def test_rejects_oversized_config_file(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="wb") as f:
            # Создаем файл размером чуть больше 2 МБ
            f.write(b" " * (MAX_CONFIG_FILE_SIZE + 1024))
            oversized_path = Path(f.name)

        try:
            manager = ConfigManager(config_path=oversized_path)
            loaded = manager.load_config(force_reload=True)
            self.assertEqual(loaded["version"], DEFAULT_CONFIG["version"])
        finally:
            oversized_path.unlink(missing_ok=True)

    def test_rejects_saving_to_directory_or_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir)
            manager = ConfigManager(config_path=dir_path)
            # Не должен выбрасывать исключение, безопасно логирует предупреждение
            manager.save_config({"version": 1})


class TestInputFlowSecurity(unittest.TestCase):
    """Тестирование защиты от длинных строк и DoS-атак на регуляторный конвейер."""

    def test_registry_normalize_limits_length(self) -> None:
        huge_text = "а" * (MAX_COMMAND_INPUT_LENGTH + 2000)
        registry = CommandRegistry()
        normalized = registry._normalize(huge_text)
        self.assertLessEqual(len(normalized), MAX_COMMAND_INPUT_LENGTH)

    def test_input_flow_handle_limits_length(self) -> None:
        huge_text = "да " * 1000
        words = answer_words(huge_text)
        self.assertIn("да", words)

        registry_mock = MagicMock()
        registry_mock.exact_match.return_value = None
        registry_mock.suggest.return_value = None
        flow = InputFlow(registry=registry_mock)
        result = flow.handle(huge_text)
        self.assertTrue(result.startswith("Ты сказал: "))
        self.assertLessEqual(len(result), MAX_INPUT_TEXT_LENGTH + len("Ты сказал: "))


if __name__ == "__main__":
    unittest.main()
