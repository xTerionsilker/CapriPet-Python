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


if __name__ == "__main__":
    unittest.main()
