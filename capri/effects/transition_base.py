"""Базовые цветовые константы и пиксельные утилиты для визуальных эффектов."""

from __future__ import annotations

from ..ui.draw_utils import (
    PIXEL_SIZE,
    snap_pixel,
    snap_point,
    with_alpha,
)
from ..ui.theme import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_NEON_VIOLET,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
    PALETTE_COLORS,
    PALETTE_WEIGHTS,
    pick_palette_color,
)

COLOR_VIOLET = COLOR_NEON_VIOLET

DURATION_OUT_MS = 840
DURATION_IN_MS = 1000
DURATION_POINT_MS = 900
DURATION_ERRATIC_MS = 1750
DURATION_DODGE_MS = 260

BAYER_4X4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)

__all__ = [
    "BAYER_4X4",
    "COLOR_ACID_GREEN",
    "COLOR_CRIMSON",
    "COLOR_ELECTRIC_BLUE",
    "COLOR_OBSIDIAN",
    "COLOR_VIOLET",
    "COLOR_WHITE",
    "DURATION_DODGE_MS",
    "DURATION_ERRATIC_MS",
    "DURATION_IN_MS",
    "DURATION_OUT_MS",
    "DURATION_POINT_MS",
    "PALETTE_COLORS",
    "PALETTE_WEIGHTS",
    "PIXEL_SIZE",
    "pick_palette_color",
    "snap_pixel",
    "snap_point",
    "with_alpha",
]
