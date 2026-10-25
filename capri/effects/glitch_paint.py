from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen

COLORS = ("#39ff6a", "#ff1e46", "#a259ff", "#eaffef")
NOISE = ("#39ff6a", "#ff1e46", "#ffffff", "#a259ff")


def paint_frame(painter: QPainter, width: int, height: int) -> None:
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


def paint_tears(painter: QPainter, width: int, height: int) -> None:
    count = 1 if random.random() < 0.45 else 0
    for _ in range(count):
        y = random.randint(0, height - 1)
        band = random.randint(1, 4)
        tint = QColor(random.choice(COLORS))
        tint.setAlpha(random.randint(10, 22))
        painter.fillRect(0, y, width, band, tint)


def paint_slices(painter: QPainter, width: int, height: int) -> None:
    count = random.randint(2, 6)
    for _ in range(count):
        y = random.randint(0, height - 1)
        slice_height = random.randint(1, 3)
        slice_width = random.randint(
            width // 12, max(width // 12 + 1, width // 2)
        )
        x = random.randint(0, max(0, width - slice_width))
        color = QColor(random.choice(COLORS))
        color.setAlpha(random.randint(14, 34))
        painter.fillRect(x, y, slice_width, slice_height, color)

        ghost = QColor(color)
        ghost.setAlpha(max(4, color.alpha() // 3))
        painter.fillRect(
            max(0, min(width - 1, x + random.randint(-120, 120))),
            y,
            min(slice_width, width),
            1,
            ghost,
        )


def paint_scanlines(
    painter: QPainter, width: int, height: int
) -> None:
    alpha = random.randint(7, 13)
    painter.setPen(QPen(QColor(57, 255, 106, alpha)))
    for y in range(0, height, 3):
        painter.drawLine(0, y, width, y)


def paint_noise(painter: QPainter, width: int, height: int) -> None:
    base = max(18, min(80, width * height // 60000))
    count = random.randint(int(base * 0.8), int(base * 1.3))
    count = min(count, 1300)
    for _ in range(count):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        fleck = QColor(random.choice(NOISE))
        fleck.setAlpha(random.randint(30, 80))
        painter.fillRect(x, y, 1, 1, fleck)


def paint_bars(painter: QPainter, width: int, height: int) -> None:
    if random.random() >= 0.06:
        return
    y = random.randint(0, height - 1)
    main = QColor(random.choice(COLORS[:3]))
    main.setAlpha(60)
    painter.fillRect(0, y, width, 1, main)
    fringe = QColor(random.choice(COLORS[:3]))
    fringe.setAlpha(35)
    painter.fillRect(0, y + 1, width, 1, fringe)
    painter.fillRect(0, max(0, y - 1), width, 1, fringe)


def paint_wild_frame(painter: QPainter, width: int, height: int) -> None:
    painter.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_SourceOver
    )
    painter.fillRect(
        0, 0, width, height, QColor(0, 0, 0, 220)
    )

    for _ in range(40):
        paint_tears(painter, width, height)
    for _ in range(30):
        paint_slices(painter, width, height)
    paint_scanlines(painter, width, height)
    for _ in range(10):
        paint_noise(painter, width, height)
    for _ in range(40):
        paint_bars(painter, width, height)