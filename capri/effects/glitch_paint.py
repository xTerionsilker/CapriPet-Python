from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from .transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
    PIXEL_SIZE,
    pick_palette_color,
    snap_pixel,
)

# Выборка киберпанк HUD-текстов для редких микро-артефактов (в духе Cyberpunk 2077 HUD)
_HUD_MICRO_TAGS = (
    "RELIC_2.0 // SYNC",
    "KIROSHI_OPTICS // OK",
    "BUFFER_OVRFLW [0x7F]",
    "NET_PULSE // 0.18ms",
    "DAEMON_PROT // ACTIVE",
    "MEM_CORRUPT: 0x3F",
    "NEURAL_LINK :: 99.4%",
    "TRACE_ROUTE // ICE",
)


def paint_frame(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    """Фоновый киберпанк-глитч экрана в стилистике Cyberpunk 2077:

    деликатные микро-помехи интерфейса Kiroshi / Relic, сканлайны, шины данных и
    микро-маркеры телеметрии в строгой палитре Капри с настраиваемой силой (weak/medium/strong).
    """
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    painter.fillRect(0, 0, width, height, Qt.GlobalColor.transparent)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    paint_scanlines(painter, width, height, intensity)
    paint_kiroshi_brackets(painter, width, height, intensity)
    paint_slices(painter, width, height, intensity)
    paint_tears(painter, width, height, intensity)
    paint_circuit_traces(painter, width, height, intensity)
    paint_cyber_markers(painter, width, height, intensity)
    paint_subtle_noise(painter, width, height, intensity)


def paint_scanlines(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    """Интерлейсные сканлайны оптики Kiroshi."""
    pen_color = QColor(COLOR_OBSIDIAN)
    if intensity == "strong":
        pen_color.setAlpha(random.randint(12, 22))
        step = PIXEL_SIZE
    elif intensity == "medium":
        pen_color.setAlpha(random.randint(8, 16))
        step = PIXEL_SIZE * 2
    else:  # weak
        pen_color.setAlpha(random.randint(6, 12))
        step = PIXEL_SIZE * 2

    painter.setPen(QPen(pen_color, 1))
    for y in range(0, height, step):
        painter.drawLine(0, y, width, y)


def paint_tears(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    """Горизонтальные разрывы кадра (tearing) в палитре персонажа."""
    chance = 0.40 if intensity == "strong" else (0.28 if intensity == "medium" else 0.18)
    if random.random() >= chance:
        return

    count = random.randint(1, 2) if intensity == "strong" else 1
    for _ in range(count):
        y = snap_pixel(random.randint(0, max(0, height - 1)))
        band = random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)) if intensity == "strong" else PIXEL_SIZE
        tint = QColor(pick_palette_color())
        alpha_range = (
            (16, 35) if intensity == "strong" else ((12, 25) if intensity == "medium" else (8, 18))
        )
        tint.setAlpha(random.randint(*alpha_range))
        painter.fillRect(0, y, width, band, tint)


def paint_slices(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    """Компактные прямоугольные полосы передачи данных / Relic десинхронизации."""
    chance = 0.65 if intensity == "strong" else (0.50 if intensity == "medium" else 0.40)
    if random.random() >= chance:
        return

    if intensity == "strong":
        count = random.randint(2, 4)
    elif intensity == "medium":
        count = random.randint(1, 3)
    else:  # weak
        count = random.randint(1, 2)

    for _ in range(count):
        y = snap_pixel(random.randint(0, max(0, height - 1)))
        slice_height = (
            random.choice((PIXEL_SIZE, PIXEL_SIZE * 2))
            if intensity == "strong"
            else PIXEL_SIZE
        )
        max_div = 3 if intensity == "strong" else 4
        slice_width = snap_pixel(
            random.randint(width // 15, max(width // 15 + 1, width // max_div))
        )
        x = snap_pixel(random.randint(0, max(0, width - slice_width)))

        color = QColor(pick_palette_color())
        alpha_range = (
            (24, 48) if intensity == "strong" else ((20, 38) if intensity == "medium" else (16, 32))
        )
        color.setAlpha(random.randint(*alpha_range))
        painter.fillRect(x, y, slice_width, slice_height, color)

        # Тонкий хроматический след Cyberpunk 2077 (хроматическое расслоение алый/синий)
        ghost_chance = 0.85 if intensity == "strong" else 0.65
        if random.random() < ghost_chance:
            ghost_color = QColor(
                COLOR_CRIMSON if random.random() < 0.75 else COLOR_ELECTRIC_BLUE
            )
            ghost_color.setAlpha(random.randint(10, 24))
            ghost_offset = random.choice((-24, -16, -8, 8, 16, 24)) if intensity == "strong" else random.choice((-16, -8, 8, 16))
            gx = max(0, min(width - 1, x + ghost_offset))
            gw = min(slice_width // 2, width - gx)
            if gw > 0:
                painter.fillRect(gx, y, gw, slice_height, ghost_color)


def paint_circuit_traces(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    """Шины передачи данных Cyberpunk: L-образные или линейные сегменты с терминальными узлами."""
    chance = 0.35 if intensity == "strong" else (0.24 if intensity == "medium" else 0.15)
    if random.random() >= chance:
        return

    y = snap_pixel(random.randint(height // 10, max(height // 10 + 1, height - height // 10)))
    x1 = snap_pixel(random.randint(0, max(0, width - width // 3)))
    w = snap_pixel(random.randint(width // 8, width // 3))

    color = QColor(COLOR_ACID_GREEN if random.random() < 0.65 else COLOR_CRIMSON)
    alpha_range = (
        (30, 55) if intensity == "strong" else ((25, 45) if intensity == "medium" else (20, 38))
    )
    color.setAlpha(random.randint(*alpha_range))
    painter.fillRect(x1, y, w, PIXEL_SIZE, color)

    # L-образный изгиб шины Cyberpunk
    if random.random() < 0.6:
        bend_len = PIXEL_SIZE * random.randint(3, 7)
        dir_y = 1 if (y + bend_len < height) else -1
        painter.fillRect(x1 + w - PIXEL_SIZE, y, PIXEL_SIZE, bend_len * dir_y, color)
        # Конечный терминальный блок
        node_y = y + (bend_len * dir_y)
        painter.fillRect(x1 + w - PIXEL_SIZE * 2, node_y, PIXEL_SIZE * 3, PIXEL_SIZE, color)
    else:
        # Прямоугольная терминальная точка
        painter.fillRect(x1 + w, y - PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 3, color)


def paint_kiroshi_brackets(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    """Угловые прицельные скобки интерфейса Kiroshi Optics по углам или в случайных секторах."""
    chance = 0.28 if intensity == "strong" else (0.18 if intensity == "medium" else 0.12)
    if random.random() >= chance:
        return

    # Выбираем позицию: либо угловые зоны экрана, либо случайная точка
    if random.random() < 0.6:
        # Угловой отступ
        margin = 32
        corner = random.choice(((margin, margin), (width - margin - 40, margin),
                               (margin, height - margin - 40), (width - margin - 40, height - margin - 40)))
        bx, by = corner
    else:
        bx = snap_pixel(random.randint(width // 8, max(width // 8 + 1, width - width // 4)))
        by = snap_pixel(random.randint(height // 8, max(height // 8 + 1, height - height // 4)))

    size = PIXEL_SIZE * random.randint(3, 5)
    bracket_color = QColor(COLOR_CRIMSON if random.random() < 0.75 else COLOR_ACID_GREEN)
    alpha_range = (
        (35, 60) if intensity == "strong" else ((28, 50) if intensity == "medium" else (22, 45))
    )
    bracket_color.setAlpha(random.randint(*alpha_range))

    # Рисуем угол интерфейса
    painter.fillRect(bx, by, size, PIXEL_SIZE, bracket_color)
    painter.fillRect(bx, by, PIXEL_SIZE, size, bracket_color)

    # Маленькая прицельная точка рядом
    dot_color = QColor(COLOR_WHITE)
    dot_color.setAlpha(random.randint(25, 50))
    painter.fillRect(bx + size + PIXEL_SIZE, by + PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE, dot_color)


def paint_cyber_markers(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    """Деликатные микро-метки телеметрии Cyberpunk 2077 (шрифт, координаты, системные теги)."""
    chance = 0.20 if intensity == "strong" else (0.13 if intensity == "medium" else 0.08)
    if random.random() >= chance:
        return

    x = snap_pixel(random.randint(width // 10, max(width // 10 + 1, width - width // 3)))
    y = snap_pixel(random.randint(height // 10, max(height // 10 + 1, height - height // 10)))

    tag = random.choice(_HUD_MICRO_TAGS)
    font = QFont("monospace", 7, QFont.Weight.Bold)
    painter.setFont(font)

    text_color = QColor(COLOR_CRIMSON if random.random() < 0.70 else COLOR_ACID_GREEN)
    alpha_range = (
        (45, 75) if intensity == "strong" else ((35, 65) if intensity == "medium" else (30, 55))
    )
    text_color.setAlpha(random.randint(*alpha_range))
    painter.setPen(text_color)
    painter.drawText(x, y, tag)

    # Акцентная полоска под текстом
    bar_w = PIXEL_SIZE * random.randint(4, 10)
    painter.fillRect(x, y + 3, bar_w, 2, text_color)


def paint_subtle_noise(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    """Шум цифровой памяти."""
    if intensity == "strong":
        count = random.randint(20, 50)
        alpha_range = (25, 65)
    elif intensity == "medium":
        count = random.randint(12, 30)
        alpha_range = (20, 50)
    else:  # weak
        count = random.randint(6, 18)
        alpha_range = (15, 45)

    for _ in range(count):
        x = snap_pixel(random.randint(0, max(0, width - 1)))
        y = snap_pixel(random.randint(0, max(0, height - 1)))
        fleck = QColor(pick_palette_color())
        fleck.setAlpha(random.randint(*alpha_range))
        painter.fillRect(x, y, PIXEL_SIZE, PIXEL_SIZE, fleck)
