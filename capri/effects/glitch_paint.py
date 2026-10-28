from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

COLORS = ("#39ff6a", "#ff1e46", "#a259ff", "#eaffef")
NOISE = ("#39ff6a", "#ff1e46", "#ffffff", "#a259ff")

# Цвета для дикого/хоррор глитча: адский красный, ядовитый розовый, мертвенно-чёрный, кислотный зелёный, кровь
WILD_COLORS = (
    QColor(255, 0, 30),
    QColor(255, 20, 70),
    QColor(220, 0, 0),
    QColor(180, 0, 20),
    QColor(255, 0, 140),
    QColor(0, 0, 0),
    QColor(10, 0, 5),
    QColor(0, 255, 65),
    QColor(255, 255, 255),
)

CREEPY_WORDS = (
    "ERROR",
    "HELP ME",
    "CAPRI",
    "CAN YOU HEAR ME?",
    "IT BURNS",
    "RUN",
    "01000011",
    "CORRUPTED",
    "LOOK AT ME",
    "NO SIGNAL",
    "DON'T LEAVE",
    "VOID",
    "DIE",
    "DECAY",
    "SYSTEM FAILURE",
    "WATCHING YOU",
)


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


# =========================================================================
# ДИКИЙ / СТРАШНЫЙ ГЛИТЧ (Хоррор-эффект: стробоскопы, кровь, искажения, жуткие надписи)
# =========================================================================

def paint_wild_frame(painter: QPainter, width: int, height: int) -> None:
    painter.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_SourceOver
    )

    # 1. Стробоскоп и фон: чередование темных блэкаутов, красных вспышек и негативов
    roll = random.random()
    if roll < 0.40:
        # Темный блэкаут
        bg_alpha = random.randint(180, 240)
        painter.fillRect(0, 0, width, height, QColor(0, 0, 0, bg_alpha))
    elif roll < 0.65:
        # Кроваво-красная заливка вспышки
        flash_alpha = random.randint(100, 210)
        painter.fillRect(0, 0, width, height, QColor(190, 0, 25, flash_alpha))
    elif roll < 0.75:
        # Ядовито-розовая вспышка
        flash_alpha = random.randint(80, 160)
        painter.fillRect(0, 0, width, height, QColor(255, 0, 120, flash_alpha))
    elif roll < 0.82:
        # Белый резкий строб
        strobe_alpha = random.randint(140, 230)
        painter.fillRect(0, 0, width, height, QColor(255, 255, 255, strobe_alpha))
    else:
        # Полупрозрачная дымка
        painter.fillRect(0, 0, width, height, QColor(5, 0, 10, 120))

    # 2. Крупные агрессивные полосы искажения (Horizontal tearing & displacement blocks)
    for _ in range(random.randint(15, 30)):
        by = random.randint(0, height - 1)
        bh = random.choice((2, 4, 8, 16, 32, 64))
        bw = random.randint(width // 4, width)
        bx = random.randint(-100, width - bw + 100)
        color = QColor(random.choice(WILD_COLORS))
        color.setAlpha(random.randint(160, 255))
        painter.fillRect(bx, by, bw, bh, color)

    # 3. Черные блоки полного поглощения (Blackout void strips)
    for _ in range(random.randint(8, 18)):
        vy = random.randint(0, height - 1)
        vh = random.choice((12, 24, 48, 90))
        painter.fillRect(0, vy, width, vh, QColor(0, 0, 0, random.randint(220, 255)))

    # 4. Сверхплотный цифровой шум и битые пиксели (Heavy digital static)
    noise_count = random.randint(400, 900)
    for _ in range(noise_count):
        nx = random.randint(0, width - 1)
        ny = random.randint(0, height - 1)
        ns = random.choice((2, 4, 6, 8))
        color = QColor(random.choice(WILD_COLORS))
        color.setAlpha(random.randint(180, 255))
        painter.fillRect(nx, ny, ns, ns, color)

    # 5. Пиксельные молнии / электрические разряды через экран
    if random.random() < 0.70:
        for _ in range(random.randint(2, 5)):
            pen = QPen(random.choice((QColor(255, 255, 255, 240), QColor(255, 0, 60, 220), QColor(0, 255, 65, 200))), random.choice((2, 4, 6)))
            painter.setPen(pen)
            cur_x = random.randint(0, width)
            cur_y = 0
            while cur_y < height:
                nxt_x = max(0, min(width, cur_x + random.randint(-80, 80)))
                nxt_y = cur_y + random.randint(20, 70)
                # Ступенчатая молния
                mid_x = nxt_x
                mid_y = cur_y
                painter.drawLine(cur_x, cur_y, mid_x, mid_y)
                painter.drawLine(mid_x, mid_y, nxt_x, nxt_y)
                cur_x, cur_y = nxt_x, nxt_y

    # 6. Жуткие глитч-надписи (Creepy glitch typography)
    if random.random() < 0.75:
        font_size = random.choice((28, 42, 64, 88, 120))
        font = QFont("Press Start 2P")
        font.setPixelSize(font_size)
        font.setBold(True)
        painter.setFont(font)

        phrase = random.choice(CREEPY_WORDS)
        tx = random.randint(50, max(51, width - 500))
        ty = random.randint(font_size + 20, height - 40)

        # Хроматическая аберрация текста (красный / голубой / белый со сдвигом)
        shift_x = random.randint(-14, 14)
        shift_y = random.randint(-6, 6)

        painter.setPen(QColor(255, 0, 50, random.randint(200, 255)))
        painter.drawText(tx - shift_x, ty - shift_y, phrase)

        painter.setPen(QColor(0, 255, 120, random.randint(180, 240)))
        painter.drawText(tx + shift_x, ty + shift_y, phrase)

        painter.setPen(QColor(255, 255, 255, random.randint(220, 255)))
        painter.drawText(tx, ty, phrase)

    # 7. Агрессивные тяжелые горизонтальные сканлайны
    scan_alpha = random.randint(40, 90)
    painter.setPen(QPen(QColor(0, 0, 0, scan_alpha), 2))
    for y in range(0, height, 4):
        painter.drawLine(0, y, width, y)
