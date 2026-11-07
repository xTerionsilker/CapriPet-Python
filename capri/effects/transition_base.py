"""Базовые цветовые константы и пиксельные утилиты для визуальных эффектов."""

from __future__ import annotations

import random

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor

PIXEL_SIZE = 4

COLOR_CRIMSON = QColor("#F6023F")
COLOR_OBSIDIAN = QColor("#020106")
COLOR_ACID_GREEN = QColor("#06F868")
COLOR_WHITE = QColor("#F9F9F9")
COLOR_ELECTRIC_BLUE = QColor("#126EE9")
COLOR_VIOLET = QColor("#9E1FDE")

PALETTE_COLORS = (
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_ACID_GREEN,
    COLOR_WHITE,
    COLOR_ELECTRIC_BLUE,
    COLOR_VIOLET,
)

PALETTE_WEIGHTS = (45.0, 35.0, 16.0, 2.0, 1.5, 0.5)


def pick_palette_color() -> QColor:
    """Выбирает случайный цвет палитры с учетом киберпанк-весов."""
    return random.choices(PALETTE_COLORS, weights=PALETTE_WEIGHTS, k=1)[0]


def snap_pixel(val: float | int, step: int = PIXEL_SIZE) -> int:
    """Выравнивает координату по пиксельной сетке."""
    return int(round(val / step)) * step


def snap_point(pt: QPoint, step: int = PIXEL_SIZE) -> QPoint:
    """Выравнивает точку по пиксельной сетке."""
    return QPoint(snap_pixel(pt.x(), step), snap_pixel(pt.y(), step))


def with_alpha(color: QColor, alpha: int) -> QColor:
    """Возвращает копию цвета с установленной альфа-прозрачностью (0..255)."""
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c

DURATION_OUT_MS = 840
DURATION_IN_MS = 1000
DURATION_POINT_MS = 900
DURATION_ERRATIC_MS = 1750

BAYER_4X4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)
