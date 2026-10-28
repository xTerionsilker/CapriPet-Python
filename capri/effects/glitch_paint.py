from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from .transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    PIXEL_SIZE,
    pick_palette_color,
    snap_pixel,
)

# Киберпанк-телеметрия, диагностика ядра и сетевые протоколы
CYBER_WORDS = (
    "SYS//OVERCLOCK",
    "NET_LINK//CORRUPT",
    "KERNEL_PANIC",
    "0xDEADBEEF",
    "CAPRI_CORE//ACTIVE",
    "BUFFER_OVERFLOW",
    "SYNAPSE_DESYNC",
    "HOLO_MATRIX//BURST",
    "DATA_BUS//FAULT",
    "NEURAL_LINK: 99.9%",
    "CRITICAL_OVERHEAT",
    "01000011 01000001",
    "01010000 01010010 01001001",
    "CHIP_VOLTAGE: ERR",
    "PORT: 0x7F//BREACH",
    "PROTOCOL_BYPASS",
    "MEMORY_DUMP",
    "QUANTUM_JITTER",
    "SIGNAL//INTERCEPT",
    "GRID_OVERLOAD: 120%",
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


# =========================================================================
# ДИКИЙ КИБЕРПАНК-ГЛИТЧ (Режим перегрузки: стробоскопы, Манхэттенские молнии,
# телеметрия, хроматические взрывы, обсидиановые блэкауты)
# =========================================================================

def paint_wild_frame(painter: QPainter, width: int, height: int) -> None:
    """Полная киберпанк-перегрузка экрана с соблюдением палитры Капри."""
    painter.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_SourceOver
    )

    # 1. Стробоскоп и фон: распределение строго по весам палитры Капри
    # #F20D2E (45%), #0B0B0B (35%), #3CF12B (16%), #FFFFFF (2%), #1E70F0 (1.5%), #9922EE (0.5%)
    strobe_roll = random.random()
    if strobe_roll < 0.45:
        # Алая вспышка перегрузки (#F20D2E)
        painter.fillRect(
            0, 0, width, height,
            QColor(COLOR_CRIMSON.red(), COLOR_CRIMSON.green(), COLOR_CRIMSON.blue(), random.randint(120, 220))
        )
    elif strobe_roll < 0.80:
        # Обсидиановый блэкаут (#0B0B0B)
        painter.fillRect(
            0, 0, width, height,
            QColor(COLOR_OBSIDIAN.red(), COLOR_OBSIDIAN.green(), COLOR_OBSIDIAN.blue(), random.randint(190, 245))
        )
    elif strobe_roll < 0.96:
        # Кислотно-зеленый всплеск данных (#3CF12B)
        painter.fillRect(
            0, 0, width, height,
            QColor(COLOR_ACID_GREEN.red(), COLOR_ACID_GREEN.green(), COLOR_ACID_GREEN.blue(), random.randint(90, 180))
        )
    elif strobe_roll < 0.98:
        # Ослепительный белый строб перегрузки (#FFFFFF)
        painter.fillRect(0, 0, width, height, QColor(255, 255, 255, random.randint(160, 240)))
    elif strobe_roll < 0.995:
        # Высоковольтный синий (#1E70F0)
        painter.fillRect(
            0, 0, width, height,
            QColor(COLOR_ELECTRIC_BLUE.red(), COLOR_ELECTRIC_BLUE.green(), COLOR_ELECTRIC_BLUE.blue(), random.randint(110, 190))
        )
    else:
        # Редкий ультрафиолетовый импульс (#9922EE)
        painter.fillRect(
            0, 0, width, height,
            QColor(COLOR_VIOLET.red(), COLOR_VIOLET.green(), COLOR_VIOLET.blue(), random.randint(120, 190))
        )

    # 2. Крупные агрессивные полосы искажения, выровненные по пиксельной сетке
    for _ in range(random.randint(16, 32)):
        by = snap_pixel(random.randint(0, max(0, height - 1)))
        bh = random.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 4, PIXEL_SIZE * 8, PIXEL_SIZE * 16))
        bw = snap_pixel(random.randint(width // 4, width))
        bx = snap_pixel(random.randint(-100, max(0, width - bw + 100)))
        color = QColor(pick_palette_color())
        color.setAlpha(random.randint(170, 255))
        painter.fillRect(bx, by, bw, bh, color)

    # 3. Черные блоки полного поглощения (Обсидиановый вакуум)
    for _ in range(random.randint(8, 16)):
        vy = snap_pixel(random.randint(0, max(0, height - 1)))
        vh = random.choice((PIXEL_SIZE * 3, PIXEL_SIZE * 6, PIXEL_SIZE * 12, PIXEL_SIZE * 24))
        painter.fillRect(0, vy, width, vh, QColor(COLOR_OBSIDIAN.red(), COLOR_OBSIDIAN.green(), COLOR_OBSIDIAN.blue(), random.randint(220, 255)))

    # 4. Сверхплотный цифровой шум и битые пиксели
    noise_count = random.randint(450, 950)
    for _ in range(noise_count):
        nx = snap_pixel(random.randint(0, max(0, width - 1)))
        ny = snap_pixel(random.randint(0, max(0, height - 1)))
        ns = random.choice((PIXEL_SIZE, PIXEL_SIZE * 2))
        color = QColor(pick_palette_color())
        color.setAlpha(random.randint(180, 255))
        painter.fillRect(nx, ny, ns, ns, color)

    # 5. Манхэттенские пиксельные кибер-молнии (строго 90° и 45° шаги)
    if random.random() < 0.75:
        for _ in range(random.randint(2, 5)):
            bolt_color = pick_palette_color()
            pen = QPen(bolt_color, PIXEL_SIZE)
            pen.setCapStyle(Qt.PenCapStyle.SquareCap)
            painter.setPen(pen)

            cur_x = snap_pixel(random.randint(0, width))
            cur_y = 0
            while cur_y < height:
                nxt_x = snap_pixel(max(0, min(width, cur_x + random.choice((-80, -48, -24, 0, 24, 48, 80)))))
                nxt_y = snap_pixel(cur_y + random.randint(24, 80))
                # Манхэттенская ступень
                painter.drawLine(cur_x, cur_y, nxt_x, cur_y)
                painter.drawLine(nxt_x, cur_y, nxt_x, nxt_y)
                # Узловой чип-блок
                if random.random() < 0.4:
                    painter.fillRect(nxt_x - PIXEL_SIZE, nxt_y - PIXEL_SIZE, PIXEL_SIZE * 3, PIXEL_SIZE * 3, bolt_color)
                cur_x, cur_y = nxt_x, nxt_y

    # 6. Киберпанк-телеметрия и глитч-шрифты с тройным RGB-разделением
    if random.random() < 0.80:
        font_size = random.choice((28, 44, 64, 88, 112))
        font = QFont("Press Start 2P")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(font_size)
        font.setBold(True)
        painter.setFont(font)

        phrase = random.choice(CYBER_WORDS)
        tx = snap_pixel(random.randint(40, max(41, width - 600)))
        ty = snap_pixel(random.randint(font_size + 20, max(font_size + 21, height - 40)))

        # Хроматическое смещение текста
        shift = snap_pixel(random.choice((4, 8, 12, 16)))

        # Левый алый слой (#F20D2E)
        painter.setPen(QColor(COLOR_CRIMSON.red(), COLOR_CRIMSON.green(), COLOR_CRIMSON.blue(), random.randint(200, 255)))
        painter.drawText(tx - shift, ty - shift // 2, phrase)

        # Правый зеленый слой (#3CF12B)
        painter.setPen(QColor(COLOR_ACID_GREEN.red(), COLOR_ACID_GREEN.green(), COLOR_ACID_GREEN.blue(), random.randint(190, 255)))
        painter.drawText(tx + shift, ty + shift // 2, phrase)

        # Центральный белый/алый слой перегрузки
        center_color = COLOR_WHITE if random.random() < 0.5 else COLOR_CRIMSON
        painter.setPen(QColor(center_color.red(), center_color.green(), center_color.blue(), random.randint(220, 255)))
        painter.drawText(tx, ty, phrase)

    # 7. Тяжелые горизонтальные сканлайны
    scan_alpha = random.randint(40, 90)
    painter.setPen(QPen(QColor(COLOR_OBSIDIAN.red(), COLOR_OBSIDIAN.green(), COLOR_OBSIDIAN.blue(), scan_alpha), 2))
    for y in range(0, height, PIXEL_SIZE):
        painter.drawLine(0, y, width, y)
