"""Тесты монопольного использования семейства шрифтов Exo 2."""

from __future__ import annotations

from pathlib import Path
import unittest

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from capri.ui.theme import (
    FONT_FAMILY,
    get_font,
    get_hud_font,
    get_terminal_font,
    get_ui_font,
    init_fonts,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN_FAMILIES = (
    "JetBrains Mono",
    "Press Start 2P",
    "Terminus",
    "Segoe UI",
    "Arial",
    "Consolas",
    "Courier",
)


class TestExoFontUsage(unittest.TestCase):
    """Проверка загрузки и монопольного использования Exo 2."""

    @classmethod
    def setUpClass(cls) -> None:
        if QApplication.instance() is None:
            cls._app = QApplication([])
        else:
            cls._app = QApplication.instance()
        init_fonts()

    def test_fonts_directory_contains_only_exo(self) -> None:
        fonts_dir = _PROJECT_ROOT / "assets" / "fonts"
        self.assertTrue(fonts_dir.is_dir())
        ttf_files = list(fonts_dir.glob("*.ttf"))
        self.assertGreaterEqual(len(ttf_files), 3)
        for ttf in ttf_files:
            self.assertTrue(ttf.name.startswith("Exo2-"), f"Unexpected font: {ttf.name}")

    def test_theme_font_family_is_registered(self) -> None:
        self.assertEqual(FONT_FAMILY, "Exo 2")
        families = QFontDatabase.families()
        self.assertIn("Exo 2", families)

    def test_get_font_helpers_return_exo(self) -> None:
        for font_fn in (get_font, get_hud_font, get_terminal_font, get_ui_font):
            font = font_fn()
            self.assertEqual(font.family(), "Exo 2")

    def test_no_forbidden_font_families_in_capri_source(self) -> None:
        capri_dir = _PROJECT_ROOT / "capri"
        violations: list[str] = []
        for py_path in capri_dir.rglob("*.py"):
            content = py_path.read_text(encoding="utf-8")
            for forbidden in _FORBIDDEN_FAMILIES:
                if forbidden in content:
                    violations.append(f"{py_path.name}: contains '{forbidden}'")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
