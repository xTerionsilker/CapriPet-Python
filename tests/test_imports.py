"""Automated runtime validation for module imports and entry point integrity."""

from __future__ import annotations

import importlib
import os
import unittest
from pathlib import Path


class TestImportIntegrity(unittest.TestCase):
    """Тест рекурсивной проверки всех импортов проекта и точки входа main.py."""

    def test_import_main_entrypoint(self) -> None:
        """Проверяет, что точка входа main.py и все её зависимости импортируются без ошибок."""
        try:
            mod = importlib.import_module("main")
            self.assertIsNotNone(mod)
        except (ImportError, AttributeError) as exc:
            self.fail(f"Сбой импорта main.py: {exc}")

    def test_import_all_capri_modules(self) -> None:
        """Рекурсивно импортирует все Python-модули в пакете capri."""
        capri_dir = Path(__file__).resolve().parent.parent / "capri"
        failed_imports: list[str] = []

        for root, _dirs, files in os.walk(capri_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue
                rel_path = Path(root, file).relative_to(capri_dir.parent)
                # Convert path to module name, e.g. capri/ui/speech_sfx.py -> capri.ui.speech_sfx
                parts = list(rel_path.with_suffix("").parts)
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                mod_name = ".".join(parts)

                try:
                    importlib.import_module(mod_name)
                except Exception as exc:  # noqa: BLE001
                    failed_imports.append(f"{mod_name} ({rel_path}): {type(exc).__name__}: {exc}")

        if failed_imports:
            self.fail(
                "Обнаружены ошибки при импорте модулей:\n"
                + "\n".join(f"  • {err}" for err in failed_imports)
            )

    def test_context_menu_no_emojis_and_has_deck(self) -> None:
        """Проверяет, что контекстное меню содержит кнопку дэки и не содержит эмодзи."""
        from unittest.mock import MagicMock

        from PySide6.QtWidgets import QApplication

        from capri.ui.context_menu import build_pet_context_menu

        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        mock_window = MagicMock()
        mock_window.open_console = MagicMock()
        mock_window.reminder_interval_range = (600_000, 3_600_000)
        mock_window.get_designated_screen.return_value = None

        menu = build_pet_context_menu(mock_window)
        all_actions = menu.actions()

        # Проверяем наличие кнопки дэки
        action_texts = [a.text() for a in all_actions]
        has_deck = any("[DECK]" in t and "команд" in t for t in action_texts)
        self.assertTrue(has_deck, f"Кнопка дэки не найдена в контекстном меню: {action_texts}")

        # Проверяем отсутствие эмодзи и спец-символов в пунктах меню
        forbidden_ranges = [
            (0x1F300, 0x1FAFF),
            (0x2600, 0x27BF),
        ]
        forbidden_chars = {0x25B6, 0x25B2, 0x2716, 0x25C7}

        def check_menu_actions(actions):
            for act in actions:
                text = act.text()
                for ch in text:
                    code = ord(ch)
                    self.assertNotIn(
                        code,
                        forbidden_chars,
                        f"Спец-символ U+{code:04X} ({ch}) в пункте '{text}'",
                    )
                    for start, end in forbidden_ranges:
                        self.assertFalse(
                            start <= code <= end,
                            f"Эмодзи U+{code:04X} ({ch}) в пункте '{text}'",
                        )
                if act.menu() is not None:
                    check_menu_actions(act.menu().actions())

        check_menu_actions(all_actions)


if __name__ == "__main__":
    unittest.main()
