from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen

from .transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    PIXEL_SIZE,
    pick_palette_color,
    snap_pixel,
)


def paint_frame(painter: QPainter, width: int, height: int) -> None:
    """Фоновый киберпанк-глитч экрана: пиксельные сканлайны, шины данных и микро-сбои."""
    painter.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_Clear
    )
    painter.fillRect(0, 0, width, height, Qt.GlobalColor.transparent)
    painter.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_SourceOver
    )

    paint_tears(painter, width, height)
    paint_slices(painter, width, height)
    paint_scanlines(painter, width, height)
    paint_noise(painter, width, height)
    paint_bars(painter, width, height)
    paint_circuit_traces(painter, width, height)


def paint_tears(painter: QPainter, width: int, height: int) -> None:
    """Горизонтальные разрывы кадра (tearing) в фирменной палитре Капри."""
    count = 1 if random.random() < 0.45 else 0
    for _ in range(count):
        y = snap_pixel(random.randint(0, max(0, height - 1)))
        band = random.choice((PIXEL_SIZE, PIXEL_SIZE * 2))
        tint = QColor(pick_palette_color())
        tint.setAlpha(random.randint(14, 30))
        painter.fillRect(0, y, width, band, tint)


def paint_slices(painter: QPainter, width: int, height: int) -> None:
    """Пиксельные полосы смещения и хроматические следы."""
    count = random.randint(2, 5)
    for _ in range(count):
        y = snap_pixel(random.randint(0, max(0, height - 1)))
        slice_height = random.choice((PIXEL_SIZE, PIXEL_SIZE * 2))
        slice_width = snap_pixel(
            random.randint(width // 10, max(width // 10 + 1, width // 2))
        )
        x = snap_pixel(random.randint(0, max(0, width - slice_width)))

        color = QColor(pick_palette_color())
        color.setAlpha(random.randint(18, 42))
        painter.fillRect(x, y, slice_width, slice_height, color)

        # Хроматический призрак смещения
        ghost = QColor(pick_palette_color())
        ghost.setAlpha(max(6, color.alpha() // 2))
        ghost_offset = random.choice((-32, -16, 16, 32))
        gx = max(0, min(width - 1, x + ghost_offset))
        painter.fillRect(gx, y, min(slice_width, width - gx), PIXEL_SIZE, ghost)


def paint_scanlines(painter: QPainter, width: int, height: int) -> None:
    """Интерлейсные сканлайны кинескопа (CRT) с выравниванием по 4px."""
    # Чередование черных полос обсидиана и редких зеленых/алых линий
    pen_color = QColor(COLOR_OBSIDIAN)
    pen_color.setAlpha(random.randint(10, 20))
    painter.setPen(QPen(pen_color, 1))
    for y in range(0, height, PIXEL_SIZE):
        painter.drawLine(0, y, width, y)


def paint_noise(painter: QPainter, width: int, height: int) -> None:
    """Пиксельный шум данных (биты памяти) в палитре Капри."""
    base = max(16, min(70, width * height // 70000))
    count = random.randint(int(base * 0.8), int(base * 1.3))
    count = min(count, 800)
    for _ in range(count):
        x = snap_pixel(random.randint(0, max(0, width - 1)))
        y = snap_pixel(random.randint(0, max(0, height - 1)))
        fleck = QColor(pick_palette_color())
        fleck.setAlpha(random.randint(35, 90))
        painter.fillRect(x, y, PIXEL_SIZE, PIXEL_SIZE, fleck)


def paint_bars(painter: QPainter, width: int, height: int) -> None:
    """Кадровые синхро-полосы с хроматической каймой."""
    if random.random() >= 0.08:
        return
    y = snap_pixel(random.randint(0, max(0, height - 1)))
    # Основная полоса (алая или зеленая)
    main_color = QColor(pick_palette_color())
    main_color.setAlpha(55)
    painter.fillRect(0, y, width, PIXEL_SIZE, main_color)

    # Кайма смещения
    fringe = QColor(COLOR_CRIMSON if main_color != COLOR_CRIMSON else COLOR_ACID_GREEN)
    fringe.setAlpha(30)
    painter.fillRect(0, y + PIXEL_SIZE, width, PIXEL_SIZE, fringe)
    if y >= PIXEL_SIZE:
        painter.fillRect(0, y - PIXEL_SIZE, width, PIXEL_SIZE, fringe)


def paint_circuit_traces(painter: QPainter, width: int, height: int) -> None:
    """Редкие тонкие цифровые шины данных на заднем плане."""
    if random.random() >= 0.12:
        return
    y = snap_pixel(random.randint(0, max(0, height - 1)))
    x1 = snap_pixel(random.randint(0, width // 2))
    w = snap_pixel(random.randint(width // 4, width // 2))
    col = QColor(COLOR_ACID_GREEN if random.random() < 0.6 else COLOR_CRIMSON)
    col.setAlpha(random.randint(25, 50))
    painter.fillRect(x1, y, w, PIXEL_SIZE, col)
    # Концевая точка узла
    painter.fillRect(x1 + w, y - PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 3, col)



