"""Процедурный генератор вертикального потока данных Blackwall (Soulkiller Memory Dump)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QFont, QPainter, QPen, QRadialGradient

from ..ui.theme import get_hud_font
from .transition_base import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    with_alpha,
)

_TELEMETRY_BANNERS = (
    "PROJECT CAPRICORN // BIOCHIP ENGRAM",
    "ARASAKA SUBSTRATE: OVERRIDDEN",
    "SOULKILLER_V4: ACTIVE SYMBIONT",
    "HOST NEURAL LINK: ESTABLISHED",
    "BLACKWALL PROTOCOL: BREACHED",
    "SYNAPSE LOAD: 100% // OVERDRIVE",
    "DATA SHREDDER // SYSTEM INTERCEPT",
)

_HEX_CHARS = "0123456789ABCDEF"


@dataclass
class _StreamColumn:
    x: int
    y_offset: float
    speed: float
    length: int
    chars: list[str]
    banner_idx: int = -1


class BlackwallDataStream:
    """Генерирует и анимирует яростный красный поток дампа памяти Blackwall."""

    def __init__(self, width: int, height: int) -> None:
        self._width = max(100, width)
        self._height = max(100, height)
        self._col_width = 24
        self._row_height = 18
        self._columns: list[_StreamColumn] = []
        self._font: QFont = get_hud_font(10, bold=True)
        self._rng = random.Random(2077)
        self._elapsed_time = 0.0
        self._init_columns()

    def resize(self, width: int, height: int) -> None:
        self._width = max(100, width)
        self._height = max(100, height)
        self._init_columns()

    def _init_columns(self) -> None:
        self._columns.clear()
        num_cols = (self._width // self._col_width) + 2
        for col_i in range(num_cols):
            x = col_i * self._col_width
            speed = self._rng.uniform(340.0, 850.0)
            length = self._rng.randint(22, 48)
            chars = [
                self._rng.choice(_HEX_CHARS) + self._rng.choice(_HEX_CHARS)
                for _ in range(length)
            ]
            banner_idx = self._rng.choice(range(len(_TELEMETRY_BANNERS))) if self._rng.random() < 0.28 else -1
            self._columns.append(
                _StreamColumn(
                    x=x,
                    y_offset=float(self._rng.randint(-self._height, 0)),
                    speed=speed,
                    length=length,
                    chars=chars,
                    banner_idx=banner_idx,
                )
            )

    def update(self, dt: float) -> None:
        self._elapsed_time += dt
        for col in self._columns:
            col.y_offset += col.speed * dt
            # Случайная мутация символов для эффекта живого дампа
            if self._rng.random() < 0.38:
                idx = self._rng.randint(0, col.length - 1)
                col.chars[idx] = self._rng.choice(_HEX_CHARS) + self._rng.choice(_HEX_CHARS)

            col_total_height = col.length * self._row_height
            if col.y_offset - col_total_height > self._height:
                col.y_offset = -self._rng.uniform(60.0, 320.0)
                col.speed = self._rng.uniform(340.0, 900.0)
                col.banner_idx = (
                    self._rng.choice(range(len(_TELEMETRY_BANNERS)))
                    if self._rng.random() < 0.30
                    else -1
                )

    def render(self, painter: QPainter, rect: QRect, alpha: float = 1.0) -> None:
        if alpha <= 0.001 or rect.width() <= 0 or rect.height() <= 0:
            return

        painter.save()

        # 1. Фоновая тьма с глубоким багровым свечением ядра
        painter.fillRect(rect, with_alpha(COLOR_OBSIDIAN, int(250 * alpha)))
        cx = rect.center().x()
        cy = rect.center().y()
        max_r = max(rect.width(), rect.height()) * 0.65
        radial = QRadialGradient(QPointF(cx, cy), max_r)
        radial.setColorAt(0.0, with_alpha(COLOR_CRIMSON, int(85 * alpha)))
        radial.setColorAt(0.5, with_alpha(COLOR_VIOLET, int(45 * alpha)))
        radial.setColorAt(1.0, with_alpha(COLOR_OBSIDIAN, 0))
        painter.fillRect(rect, radial)

        # 2. Процедурная кибер-сетка Blackwall
        grid_pen = QPen(with_alpha(COLOR_CRIMSON, int(35 * alpha)), 1)
        painter.setPen(grid_pen)
        grid_step = 48
        for gx in range(rect.left(), rect.right(), grid_step):
            painter.drawLine(gx, rect.top(), gx, rect.bottom())
        for gy in range(rect.top(), rect.bottom(), grid_step):
            painter.drawLine(rect.left(), gy, rect.right(), gy)

        # 3. Колонки шестнадцатеричного дампа памяти
        painter.setFont(self._font)
        for col in self._columns:
            if col.x < rect.left() - self._col_width or col.x > rect.right():
                continue

            for row_i in range(col.length):
                char_y = int(col.y_offset - (col.length - 1 - row_i) * self._row_height)
                if char_y < rect.top() - self._row_height or char_y > rect.bottom() + self._row_height:
                    continue

                dist_from_head = col.length - 1 - row_i
                if dist_from_head == 0:
                    char_color = with_alpha(COLOR_WHITE, int(255 * alpha))
                elif dist_from_head < 3:
                    char_color = with_alpha(COLOR_CRIMSON, int(255 * alpha))
                elif dist_from_head < 8:
                    char_color = with_alpha(COLOR_CRIMSON, int(200 * alpha))
                else:
                    fade = max(0.12, 1.0 - (dist_from_head / col.length))
                    char_color = with_alpha(COLOR_CRIMSON, int(135 * fade * alpha))

                text = col.chars[row_i]
                painter.setPen(char_color)
                painter.drawText(col.x, char_y, text)

        # 4. Системные баннеры телеметрии
        for col in self._columns:
            if col.banner_idx >= 0:
                banner_text = _TELEMETRY_BANNERS[col.banner_idx]
                by = int(col.y_offset) % max(1, self._height)
                if rect.top() <= by <= rect.bottom():
                    tag_color = with_alpha(COLOR_ACID_GREEN, int(220 * alpha))
                    painter.setPen(tag_color)
                    painter.drawText(col.x, by, f"<{banner_text}>")

        painter.restore()
