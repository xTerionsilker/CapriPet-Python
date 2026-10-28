from __future__ import annotations

import random
from dataclasses import dataclass

from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap

from ..effects.transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
    PIXEL_SIZE,
    pick_palette_color,
    snap_pixel,
)


@dataclass
class PetRenderState:
    """Состояние питомца для визуализатора."""
    is_spawning: bool = False
    is_dragging: bool = False
    is_pose_transition: bool = False
    is_surge: bool = False
    is_speaking: bool = False
    telemetry_tag: str = "[CAPRI//ONLINE]"


class PetRenderer:
    """Рендерер спрайта питомца с процедурными кибер-глитчами, сканлайнами и эффектами."""

    def render(
        self,
        painter: QPainter,
        pixmap: QPixmap,
        state: PetRenderState,
    ) -> None:
        """Отрисовывает спрайт питомца со всеми эффектами на переданный QPainter."""
        w = pixmap.width()
        h = pixmap.height()
        if w <= 0 or h <= 0 or pixmap.isNull():
            return

        severity = self._calculate_severity(state)

        # 1. Хроматическое RGB-расслоение (Holographic Chromatic Desync)
        self._draw_chromatic_aberration(painter, pixmap, severity)

        # 2. Базовый спрайт со слайсовыми смещениями (Tearing)
        self._draw_sliced_pixmap(painter, pixmap, w, h, severity)

        # 3. Внутренние глитчи по силуэту Капри (CompositionMode_SourceAtop)
        self._draw_silhouette_glitches(painter, w, h, severity, state.is_pose_transition)

        # 4. Выступающие за силуэт кибер-искры (CompositionMode_SourceOver)
        self._draw_sparks(painter, w, h, severity)

        # 5. Цифровой HUD-индикатор телеметрии
        self._draw_hud_telemetry(painter, w, h, severity, state)

    def _calculate_severity(self, state: PetRenderState) -> float:
        if state.is_spawning:
            return 1.0
        if state.is_dragging:
            return 0.85
        if state.is_pose_transition:
            return 0.75
        if state.is_surge:
            return 0.65
        if state.is_speaking:
            return 0.45
        if random.random() < 0.28:
            return random.uniform(0.35, 0.55)
        return 0.12

    def _draw_chromatic_aberration(
        self, painter: QPainter, pixmap: QPixmap, severity: float
    ) -> None:
        chroma_chance = 0.85 if severity > 0.5 else 0.35
        if severity > 0.30 and random.random() < chroma_chance:
            chroma_shift = snap_pixel(
                random.choice((-16, -12, -8, 8, 12, 16))
                if severity > 0.7
                else random.choice((-8, -4, 4, 8))
            )
            # Алый левый фантомный слой (#F20D2E)
            painter.save()
            painter.setOpacity(random.uniform(0.25, 0.45))
            painter.drawPixmap(-chroma_shift, 0, pixmap)
            painter.restore()

            # Кислотно-зеленый правый фантомный слой (#3CF12B)
            painter.save()
            painter.setOpacity(random.uniform(0.20, 0.40))
            painter.drawPixmap(chroma_shift, 0, pixmap)
            painter.restore()

    def _draw_sliced_pixmap(
        self, painter: QPainter, pixmap: QPixmap, w: int, h: int, severity: float
    ) -> None:
        tear_chance = 0.90 if severity > 0.6 else (0.45 if severity > 0.3 else 0.15)
        if random.random() < tear_chance:
            num_slices = (
                random.randint(2, 5) if severity > 0.6 else random.randint(1, 2)
            )
            slice_bounds = [0] + sorted(
                snap_pixel(
                    random.randint(
                        PIXEL_SIZE * 2, max(PIXEL_SIZE * 3, h - PIXEL_SIZE * 2)
                    )
                )
                for _ in range(num_slices)
            ) + [h]
            slice_bounds = sorted(list(set(slice_bounds)))
            for i in range(len(slice_bounds) - 1):
                sy = slice_bounds[i]
                sh = slice_bounds[i + 1] - sy
                if sh <= 0:
                    continue
                if random.random() < 0.65:
                    sdx = snap_pixel(
                        random.choice((-20, -12, -8, 8, 12, 20))
                        if severity > 0.6
                        else random.choice((-8, -4, 4, 8))
                    )
                else:
                    sdx = 0
                painter.drawPixmap(sdx, sy, pixmap, 0, sy, w, sh)
        else:
            painter.drawPixmap(0, 0, pixmap)

    def _draw_silhouette_glitches(
        self,
        painter: QPainter,
        w: int,
        h: int,
        severity: float,
        is_pose_transition: bool,
    ) -> None:
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceAtop
        )

        # а) Кибер-сканлайны CRT (каждые 4 пикселя)
        scan_alpha = (
            random.randint(25, 60) if severity > 0.4 else random.randint(15, 35)
        )
        scan_color = QColor(COLOR_OBSIDIAN)
        scan_color.setAlpha(scan_alpha)
        painter.setPen(QPen(scan_color, 1))
        for y in range(0, h, PIXEL_SIZE):
            painter.drawLine(0, y, w, y)

        # б) Горизонтальные цифровые глитч-полосы в палитре Капри
        bar_count = (
            random.randint(5, 10)
            if severity > 0.7
            else (random.randint(3, 6) if severity > 0.3 else random.randint(1, 2))
        )
        for _ in range(bar_count):
            by = snap_pixel(random.randint(0, max(0, h - PIXEL_SIZE)))
            bh = random.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 3))
            bw = snap_pixel(random.randint(w // 4, w))
            bx = snap_pixel(random.randint(0, max(0, w - bw)))
            c = QColor(pick_palette_color())
            c.setAlpha(random.randint(160, 245))
            painter.fillRect(bx, by, bw, bh, c)

        # в) Пиксельные блоки байтов памяти (Byte Dumps)
        block_count = (
            random.randint(8, 16)
            if severity > 0.6
            else (random.randint(4, 9) if severity > 0.3 else random.randint(1, 3))
        )
        for _ in range(block_count):
            bw = snap_pixel(random.choice((8, 12, 16, 24)))
            bh = snap_pixel(random.choice((4, 8, 12)))
            bx = snap_pixel(random.randint(0, max(0, w - bw)))
            by = snap_pixel(random.randint(0, max(0, h - bh)))
            c = QColor(pick_palette_color())
            c.setAlpha(random.randint(170, 255))
            painter.fillRect(bx, by, bw, bh, c)

        # г) Телеметрические микро-глифы внутри силуэта при перегрузке
        if severity > 0.5 and random.random() < 0.7:
            font = QFont("Press Start 2P")
            font.setStyleHint(QFont.StyleHint.Monospace)
            font.setPixelSize(8)
            font.setBold(True)
            painter.setFont(font)
            glyph = random.choice(("01", "FA", "ERR", "0x4F", "TX", "99%"))
            gx = snap_pixel(random.randint(w // 4, max(w // 4 + 1, 3 * w // 4)))
            gy = snap_pixel(random.randint(h // 4, max(h // 4 + 1, 3 * h // 4)))
            painter.setPen(
                QColor(COLOR_ACID_GREEN if random.random() < 0.6 else COLOR_WHITE)
            )
            painter.drawText(gx, gy, glyph)

        # д) Эффект цифровой сборки/разборки при смене позы (Байеровский дизеринг)
        if is_pose_transition:
            dissolve_color = QColor(
                COLOR_CRIMSON if random.random() < 0.6 else COLOR_OBSIDIAN
            )
            dissolve_color.setAlpha(random.randint(140, 220))
            for dy in range(0, h, PIXEL_SIZE * 2):
                for dx in range(0, w, PIXEL_SIZE * 2):
                    if random.random() < 0.4:
                        painter.fillRect(dx, dy, PIXEL_SIZE, PIXEL_SIZE, dissolve_color)

    def _draw_sparks(
        self, painter: QPainter, w: int, h: int, severity: float
    ) -> None:
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )
        spark_chance = 0.95 if severity > 0.5 else 0.45
        if random.random() < spark_chance:
            spark_n = (
                random.randint(6, 12)
                if severity > 0.7
                else (random.randint(3, 7) if severity > 0.3 else random.randint(1, 3))
            )
            for _ in range(spark_n):
                ex = snap_pixel(random.randint(0, max(0, w - PIXEL_SIZE * 2)))
                ey = snap_pixel(random.randint(0, max(0, h - PIXEL_SIZE * 2)))
                spark_color = QColor(pick_palette_color())
                spark_color.setAlpha(random.randint(180, 255))
                if random.random() < 0.6:
                    painter.fillRect(ex, ey, PIXEL_SIZE, PIXEL_SIZE, spark_color)
                else:
                    painter.fillRect(ex, ey, PIXEL_SIZE * 2, PIXEL_SIZE, spark_color)
                    painter.fillRect(
                        ex + PIXEL_SIZE, ey + PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE * 2, spark_color
                    )

    def _draw_hud_telemetry(
        self,
        painter: QPainter,
        w: int,
        h: int,
        severity: float,
        state: PetRenderState,
    ) -> None:
        if severity > 0.4 or state.is_speaking or state.is_dragging:
            font = QFont("Press Start 2P")
            font.setStyleHint(QFont.StyleHint.Monospace)
            font.setPixelSize(7)
            font.setBold(True)
            painter.setFont(font)

            tag = (
                "[DRAG//RELOCATE]"
                if state.is_dragging
                else (
                    "[TX//SPEAKING]"
                    if state.is_speaking
                    else (
                        "[REBUILD//0x1A]"
                        if state.is_pose_transition
                        else state.telemetry_tag
                    )
                )
            )
            tag_w = len(tag) * 6 + 6
            tag_h = 10
            tag_x = snap_pixel(w - tag_w - 4)
            tag_y = snap_pixel(h - 14)
            painter.fillRect(
                tag_x,
                tag_y,
                tag_w,
                tag_h,
                QColor(
                    COLOR_OBSIDIAN.red(),
                    COLOR_OBSIDIAN.green(),
                    COLOR_OBSIDIAN.blue(),
                    210,
                ),
            )
            painter.drawRect(tag_x, tag_y, tag_w, tag_h)
            tag_color = (
                COLOR_CRIMSON
                if (severity > 0.7 or state.is_dragging)
                else COLOR_ACID_GREEN
            )
            painter.setPen(tag_color)
            painter.drawText(tag_x + 3, tag_y + 8, tag)
