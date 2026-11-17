"""Тесты модуля интро-пробоя и генераторов киберпанк-окон ошибок (Issue #80)."""

from __future__ import annotations

import unittest

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from capri.effects.intro_breach_helpers import (
    CyberErrorCard,
    draw_cyber_error_card,
    draw_glitch_slice,
)


class TestIntroBreachHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QApplication.instance() is None:
            cls._app = QApplication([])
        else:
            cls._app = QApplication.instance()

    def test_cyber_error_card_defaults_and_geometry(self) -> None:
        card = CyberErrorCard(
            title="CRITICAL_EXCEPTION",
            code="0xC0000005",
            message="MEMORY_SUBSTRATE_CORRUPTION",
            rect=QRect(100, 150, 260, 90),
            spawn_time=0.2,
            border_color=QColor("#fe0929"),
        )
        self.assertEqual(card.title, "CRITICAL_EXCEPTION")
        self.assertEqual(card.code, "0xC0000005")
        self.assertEqual(card.rect.width(), 260)
        self.assertAlmostEqual(card.spawn_time, 0.2)

    def test_draw_cyber_error_card_renders_without_crash(self) -> None:
        img = QImage(800, 600, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        try:
            card = CyberErrorCard(
                title="SUBSTRATE_OVERFLOW",
                code="0xDEADBEEF",
                message="RELIC_SYNAPSE_FAULT",
                rect=QRect(50, 50, 280, 100),
                spawn_time=0.1,
                border_color=QColor("#fe0929"),
            )
            draw_cyber_error_card(painter, card, progress=0.8, glitch_power=0.0)
            draw_cyber_error_card(painter, card, progress=1.0, glitch_power=0.7)
        finally:
            painter.end()

    def test_draw_glitch_slice_renders(self) -> None:
        img = QImage(800, 600, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        try:
            draw_glitch_slice(painter, QRect(0, 0, 800, 600), slice_y=200, height=30, offset_x=15)
        finally:
            painter.end()

    def test_intro_breach_overlay_lifecycle_and_skip(self) -> None:
        from capri.effects.intro_breach_overlay import IntroBreachOverlay
        overlay = IntroBreachOverlay()
        self.assertGreater(len(overlay._error_cards), 10)
        self.assertFalse(overlay._is_skipping)
        # Проверка структуры карточек ошибок
        first = overlay._error_cards[0]
        self.assertTrue(len(first.title) > 0)
        self.assertGreater(first.rect.width(), 50)
        # Проверка симуляции тика без падений
        overlay._on_tick()
        overlay.close()


if __name__ == "__main__":
    unittest.main()
