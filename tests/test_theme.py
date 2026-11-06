from __future__ import annotations

import unittest

from capri.ui.theme import (
    ACID_GREEN,
    ELECTRIC_BLUE,
    NEON_CRIMSON,
    NEON_VIOLET,
    OBSIDIAN_BLACK,
    PURE_WHITE,
    CSS_CYBER_HUD,
    CSS_CYBER_TERMINAL,
    CSS_CYBER_UI,
)


class TestTheme(unittest.TestCase):
    def test_cyberpunk_palette_hex_codes(self) -> None:
        self.assertEqual(NEON_CRIMSON, "#F6023F")
        self.assertEqual(OBSIDIAN_BLACK, "#020106")
        self.assertEqual(ACID_GREEN, "#06F868")
        self.assertEqual(PURE_WHITE, "#F9F9F9")
        self.assertEqual(ELECTRIC_BLUE, "#126EE9")
        self.assertEqual(NEON_VIOLET, "#9E1FDE")

    def test_cyberpunk_typography_stacks(self) -> None:
        self.assertIn("sans-serif", CSS_CYBER_HUD)
        self.assertIn("sans-serif", CSS_CYBER_TERMINAL)
        self.assertIn("sans-serif", CSS_CYBER_UI)
