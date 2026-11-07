"""Отрисовка глитч-эффектов, сетки и HUD-элементов перехода."""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygon

from .transition_base import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    PIXEL_SIZE,
    snap_pixel,
    with_alpha,
)


class CyberShockwaveRing:
    """Пиксельное кольцо ударной волны для анимаций телепортации и взрывов."""

    @staticmethod
    def draw(
        painter: QPainter,
        center: QPoint,
        radius: int,
        color: QColor,
        thickness: int = PIXEL_SIZE,
    ) -> None:
        if radius <= PIXEL_SIZE:
            return

        cx, cy = center.x(), center.y()
        r = snap_pixel(radius)
        cut = snap_pixel(r // 3)

        pts = [
            QPoint(cx - r + cut, cy - r),
            QPoint(cx + r - cut, cy - r),
            QPoint(cx + r, cy - r + cut),
            QPoint(cx + r, cy + r - cut),
            QPoint(cx + r - cut, cy + r),
            QPoint(cx - r + cut, cy + r),
            QPoint(cx - r, cy + r - cut),
            QPoint(cx - r, cy - r + cut),
        ]

        pen = QPen(color, thickness)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)

        for i, p1 in enumerate(pts):
            p2 = pts[(i + 1) % len(pts)]
            painter.drawLine(p1, p2)


def chamfer_points(rect: QRect, cut: int) -> QPolygon:
    """Вычисляет многоугольник со скошенными под 45 градусов углами."""
    cut = max(2, min(cut, min(rect.width(), rect.height()) // 3))
    left_x, right_x = rect.left(), rect.right()
    top_y, bottom_y = rect.top(), rect.bottom()
    return QPolygon(
        [
            QPoint(left_x + cut, top_y),
            QPoint(right_x - cut, top_y),
            QPoint(right_x, top_y + cut),
            QPoint(right_x, bottom_y - cut),
            QPoint(right_x - cut, bottom_y),
            QPoint(left_x + cut, bottom_y),
            QPoint(left_x, bottom_y - cut),
            QPoint(left_x, top_y + cut),
        ]
    )


def draw_scanlines(
    painter: QPainter,
    rect: QRect,
    alpha: int = 34,
    spacing: int = 4,
) -> None:

    if rect.width() <= 0 or rect.height() <= 0:
        return
    line = with_alpha(COLOR_OBSIDIAN, alpha)
    y = rect.top()
    while y < rect.bottom():
        painter.fillRect(rect.left(), y, rect.width(), 1, line)
        y += spacing


def draw_scan_sweep(
    painter: QPainter,
    rect: QRect,
    progress: float,
    color: QColor = COLOR_CRIMSON,
) -> None:

    if rect.height() <= 0:
        return
    y = rect.top() + int(rect.height() * (progress % 1.0))
    for offset, alpha, height in (
        (-6, 28, 1),
        (-2, 70, 1),
        (0, 210, 2),
        (3, 90, 1),
    ):
        painter.fillRect(
            rect.left(),
            max(rect.top(), min(rect.bottom(), y + offset)),
            rect.width(),
            height,
            with_alpha(color, alpha),
        )

    rng = random.Random(int(progress * 1000) + rect.width())
    for _ in range(7):
        bx = rng.randint(rect.left(), max(rect.left(), rect.right() - 40))
        bw = rng.choice((8, 16, 32, 64))
        painter.fillRect(
            bx,
            y + rng.choice((-4, 0, 4)),
            min(bw, rect.right() - bx),
            2,
            with_alpha(
                rng.choice((COLOR_CRIMSON, COLOR_ACID_GREEN, COLOR_WHITE)),
                150,
            ),
        )


def draw_screen_glitch_bars(
    painter: QPainter,
    rect: QRect,
    progress: float,
    intensity: float = 1.0,
) -> None:

    if intensity <= 0.02 or rect.height() <= 0:
        return
    rng = random.Random(int(progress * 500) + rect.height())
    count = int(2 + 6 * intensity)
    for _ in range(count):
        y = rng.randint(rect.top(), rect.bottom())
        h = rng.choice((1, 2, 3, 6, 10))
        w = rng.randint(rect.width() // 12, max(rect.width() // 3, 2))
        x = rng.randint(rect.left(), max(rect.left(), rect.right() - w))
        color = rng.choices(
            (
                COLOR_CRIMSON,
                COLOR_OBSIDIAN,
                COLOR_ACID_GREEN,
                COLOR_ELECTRIC_BLUE,
            ),
            weights=(52, 30, 14, 4),
            k=1,
        )[0]
        painter.fillRect(
            x,
            y,
            w,
            h,
            with_alpha(color, int(rng.randint(50, 150) * intensity)),
        )


def draw_hazard_frame(
    painter: QPainter,
    rect: QRect,
    intensity: float = 1.0,
    color: QColor = COLOR_CRIMSON,
) -> None:

    if intensity <= 0.02 or rect.width() <= 0 or rect.height() <= 0:
        return
    alpha = int(210 * intensity)
    band_h = 8
    painter.save()
    painter.setClipRect(rect)
    for band_rect in (
        QRect(rect.left(), rect.top(), rect.width(), band_h),
        QRect(rect.left(), rect.bottom() - band_h, rect.width(), band_h),
    ):
        painter.fillRect(band_rect, with_alpha(COLOR_OBSIDIAN, alpha))
        stripe_w = 12
        x = band_rect.left() - band_h
        while x < band_rect.right():
            poly = QPolygon(
                [
                    QPoint(x, band_rect.bottom()),
                    QPoint(x + stripe_w // 2, band_rect.bottom()),
                    QPoint(x + stripe_w // 2 + band_h, band_rect.top()),
                    QPoint(x + band_h, band_rect.top()),
                ]
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(with_alpha(color, alpha))
            painter.drawPolygon(poly)
            x += stripe_w
    painter.restore()


class CyberHoloReticle:
    """Голографический визир захвата цели с угловыми рамками."""

    @staticmethod
    def draw(
        painter: QPainter,
        rect: QRect,
        progress: float,
        color: QColor | None = None,
        bracket_offset: int = 0,
    ) -> None:
        if rect.width() <= 0 or rect.height() <= 0:
            return

        w = rect.width()
        h = rect.height()
        cx = rect.center().x()
        cy = rect.center().y()

        corner_len = snap_pixel(max(PIXEL_SIZE * 3, min(w, h) // 4))
        thickness = PIXEL_SIZE

        box = rect.adjusted(
            -bracket_offset,
            -bracket_offset,
            bracket_offset,
            bracket_offset,
        )
        bx_l, bx_r = box.left(), box.right()
        bx_t, bx_b = box.top(), box.bottom()

        painter.setPen(Qt.PenStyle.NoPen)
        alpha = max(0, min(255, int(255 * progress)))
        base_color = color if color is not None else COLOR_CRIMSON
        c = QColor(base_color)
        c.setAlpha(alpha)

        obsidian = QColor(COLOR_OBSIDIAN)
        obsidian.setAlpha(int(alpha * 0.95))

        sh = 2
        for ox, oy in ((-sh, 0), (sh, 0), (0, -sh), (0, sh)):
            painter.fillRect(
                bx_l + ox, bx_t + oy, corner_len, thickness, obsidian
            )
            painter.fillRect(
                bx_l + ox, bx_t + oy, thickness, corner_len, obsidian
            )
            painter.fillRect(
                bx_r - corner_len + 1 + ox,
                bx_t + oy,
                corner_len,
                thickness,
                obsidian,
            )
            painter.fillRect(
                bx_r - thickness + 1 + ox,
                bx_t + oy,
                thickness,
                corner_len,
                obsidian,
            )
            painter.fillRect(
                bx_l + ox,
                bx_b - thickness + 1 + oy,
                corner_len,
                thickness,
                obsidian,
            )
            painter.fillRect(
                bx_l + ox,
                bx_b - corner_len + 1 + oy,
                thickness,
                corner_len,
                obsidian,
            )
            painter.fillRect(
                bx_r - corner_len + 1 + ox,
                bx_b - thickness + 1 + oy,
                corner_len,
                thickness,
                obsidian,
            )
            painter.fillRect(
                bx_r - thickness + 1 + ox,
                bx_b - corner_len + 1 + oy,
                thickness,
                corner_len,
                obsidian,
            )

        painter.fillRect(bx_l, bx_t, corner_len, thickness, c)
        painter.fillRect(bx_l, bx_t, thickness, corner_len, c)

        painter.fillRect(
            bx_r - corner_len + 1, bx_t, corner_len, thickness, c
        )
        painter.fillRect(
            bx_r - thickness + 1, bx_t, thickness, corner_len, c
        )

        painter.fillRect(
            bx_l, bx_b - thickness + 1, corner_len, thickness, c
        )
        painter.fillRect(
            bx_l, bx_b - corner_len + 1, thickness, corner_len, c
        )

        painter.fillRect(
            bx_r - corner_len + 1,
            bx_b - thickness + 1,
            corner_len,
            thickness,
            c,
        )
        painter.fillRect(
            bx_r - thickness + 1,
            bx_b - corner_len + 1,
            thickness,
            corner_len,
            c,
        )

        cross_sz = snap_pixel(PIXEL_SIZE * 2)
        white_c = QColor(COLOR_WHITE)
        white_c.setAlpha(alpha)
        painter.fillRect(
            cx - cross_sz,
            cy - thickness // 2,
            cross_sz * 2,
            thickness,
            white_c,
        )
        painter.fillRect(
            cx - thickness // 2,
            cy - cross_sz,
            thickness,
            cross_sz * 2,
            white_c,
        )


class CyberKiroshiReticle:
    """Визир оптики Kiroshi с круговой шкалой, вращением и метками."""

    @staticmethod
    def draw(
        painter: QPainter,
        rect: QRect,
        progress: float,
        color: QColor = COLOR_CRIMSON,
        bracket_offset: int = 0,
        rotation: float = 0.0,
        label: str | None = None,
        locked: bool = False,
    ) -> None:
        progress = max(0.0, min(1.0, progress))
        if progress <= 0.01 or rect.width() <= 0 or rect.height() <= 0:
            return

        alpha = int(255 * progress)
        shadow = with_alpha(COLOR_OBSIDIAN, int(alpha * 0.9))
        main = with_alpha(color, alpha)
        accent = with_alpha(
            COLOR_ACID_GREEN
            if color != COLOR_ACID_GREEN
            else COLOR_CRIMSON,
            int(alpha * 0.8),
        )

        CyberHoloReticle.draw(
            painter,
            rect,
            progress,
            color=color,
            bracket_offset=bracket_offset,
        )

        cx = rect.center().x()
        cy = rect.center().y()
        radius = max(
            18, min(rect.width(), rect.height()) // 2 + bracket_offset
        )
        radius = snap_pixel(radius)

        ticks = 24
        for i in range(ticks):
            ang = rotation + (math.tau * i / ticks)
            is_major = i % 6 == 0
            inner = radius + 2
            outer = radius + (12 if is_major else 6)
            x1 = cx + int(math.cos(ang) * inner)
            y1 = cy + int(math.sin(ang) * inner)
            x2 = cx + int(math.cos(ang) * outer)
            y2 = cy + int(math.sin(ang) * outer)
            tick_color = accent if is_major else main
            painter.setPen(QPen(tick_color, 2 if is_major else 1))
            painter.drawLine(x1, y1, x2, y2)

        arc_rect = QRectF(
            cx - radius - 16,
            cy - radius - 16,
            (radius + 16) * 2,
            (radius + 16) * 2,
        )
        pen = QPen(with_alpha(color, int(alpha * 0.75)), 2)
        painter.setPen(pen)
        for start in (15, 105, 195, 285):
            painter.drawArc(
                arc_rect,
                int((start + math.degrees(rotation)) * 16),
                int(38 * 16),
            )

        if label:
            font = get_hud_font(10, bold=True)
            painter.setFont(font)
            text = label.upper()
            metrics = painter.fontMetrics()
            tw = metrics.horizontalAdvance(text)
            tx = cx - tw // 2
            ty = rect.top() - 12 if rect.top() > 18 else rect.bottom() + 18
            painter.fillRect(tx - 4, ty - 11, tw + 8, 15, shadow)
            painter.setPen(with_alpha(COLOR_WHITE, alpha))
            painter.drawText(tx, ty, text)
            if locked:
                painter.fillRect(tx - 7, ty - 4, 3, 3, accent)

        if locked:
            size = snap_pixel(max(6, radius // 8))
            painter.fillRect(
                cx - size // 2,
                cy - size // 2,
                size,
                size,
                with_alpha(COLOR_WHITE, alpha),
            )
            painter.fillRect(cx - size, cy - 1, size * 2, 2, main)
            painter.fillRect(cx - 1, cy - size, 2, size * 2, main)


def draw_quickhack_panel(
    painter: QPainter,
    rect: QRect,
    progress: float,
    color: QColor = COLOR_CRIMSON,
    title: str = "QUICKHACK",
    status: str = "UPLOAD",
) -> None:

    if rect.width() < 80 or rect.height() < 18:
        return
    progress = max(0.0, min(1.0, progress))

    painter.save()
    panel = chamfer_points(rect, 7)
    painter.setPen(QPen(with_alpha(COLOR_OBSIDIAN, 240), 2))
    painter.setBrush(with_alpha(COLOR_OBSIDIAN, 205))
    painter.drawPolygon(panel)
    painter.setPen(QPen(with_alpha(color, 225), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPolygon(panel)

    font = get_hud_font(9, bold=True)
    painter.setFont(font)

    label_y = rect.top() + 12
    painter.setPen(with_alpha(COLOR_WHITE, 235))
    painter.drawText(rect.left() + 9, label_y, f"{title} // {status}")
    percent_text = f"{int(progress * 100):03d}%"
    painter.setPen(with_alpha(color, 255))
    painter.drawText(
        rect.right()
        - 9
        - painter.fontMetrics().horizontalAdvance(percent_text),
        label_y,
        percent_text,
    )

    progress_bar = QRect(rect.left() + 9, rect.bottom() - 10, rect.width() - 18, 5)
    segments = max(8, progress_bar.width() // 6)
    gap = 2
    seg_w = max(1, (progress_bar.width() - gap * (segments - 1)) // segments)
    filled = int(segments * progress)
    for i in range(segments):
        x = progress_bar.left() + i * (seg_w + gap)
        if i < filled:
            seg_color = color if i % 5 else COLOR_ACID_GREEN
            painter.fillRect(
                x,
                progress_bar.top(),
                seg_w,
                progress_bar.height(),
                with_alpha(seg_color, 240),
            )
        else:
            painter.fillRect(
                x,
                progress_bar.top(),
                seg_w,
                progress_bar.height(),
                with_alpha(COLOR_CRIMSON, 40),
            )
    painter.restore()


def draw_breach_grid(
    painter: QPainter,
    rect: QRect,
    progress: float,
    seed: int = 0,
    cell: int = 10,
    color: QColor = COLOR_ACID_GREEN,
) -> None:

    if rect.width() < cell * 2 or rect.height() < cell * 2:
        return
    painter.save()
    painter.setClipRect(rect)
    painter.fillRect(rect, with_alpha(COLOR_OBSIDIAN, 150))

    rng = random.Random(seed)
    cols = rect.width() // cell
    rows = rect.height() // cell
    for row in range(rows):
        for col in range(cols):
            r = rng.random()
            if r < progress * 0.55:
                c = (
                    color
                    if r > 0.18
                    else rng.choice(
                        (COLOR_CRIMSON, COLOR_ELECTRIC_BLUE, COLOR_VIOLET)
                    )
                )
                painter.fillRect(
                    rect.left() + col * cell + 2,
                    rect.top() + row * cell + 2,
                    cell - 4,
                    cell - 4,
                    with_alpha(c, rng.randint(90, 220)),
                )
            else:
                painter.fillRect(
                    rect.left() + col * cell + cell // 2,
                    rect.top() + row * cell + cell // 2,
                    2,
                    2,
                    with_alpha(color, 55),
                )

    line_y = rect.top() + int(rect.height() * progress)
    painter.fillRect(
        rect.left(), line_y, rect.width(), 2, with_alpha(color, 210)
    )
    painter.fillRect(
        rect.left(),
        line_y - 2,
        rect.width(),
        1,
        with_alpha(COLOR_WHITE, 120),
    )
    painter.restore()


def draw_hex_stream(
    painter: QPainter,
    rect: QRect,
    progress: float,
    columns: int = 14,
    color: QColor = COLOR_ACID_GREEN,
) -> None:

    if rect.width() <= 0 or rect.height() <= 0:
        return
    painter.save()
    painter.setClipRect(rect)
    font = get_hud_font(9, bold=True)
    painter.setFont(font)
    glyphs = "01ABCDEF<>/\\#%&"
    rng = random.Random(2077 + rect.width())
    for col in range(max(1, columns)):
        x = rect.left() + int((col + 0.5) * rect.width() / max(1, columns))
        speed = rng.uniform(0.55, 1.45)
        phase = rng.uniform(0.0, 1.0)
        head_y = (
            rect.top()
            + int(
                ((progress * speed + phase) % 1.0) * (rect.height() + 60)
            )
            - 30
        )
        for i in range(5):
            y = head_y - i * 11
            if y < rect.top() or y > rect.bottom():
                continue
            alpha = int((1.0 - i / 5.0) * 190)
            glyph_color = COLOR_WHITE if i == 0 else color
            painter.setPen(with_alpha(glyph_color, alpha))
            painter.drawText(x, y, rng.choice(glyphs))
    painter.restore()


def draw_glitch_text(
    painter: QPainter,
    x: int,
    y: int,
    text: str,
    color: QColor = COLOR_WHITE,
    size: int = 10,
) -> None:

    font = get_hud_font(size, bold=True)
    painter.save()
    painter.setFont(font)
    painter.setPen(with_alpha(COLOR_CRIMSON, 170))
    painter.drawText(x - 1, y, text)
    painter.setPen(with_alpha(COLOR_ACID_GREEN, 150))
    painter.drawText(x + 1, y, text)
    painter.setPen(with_alpha(color, 245))
    painter.drawText(x, y, text)
from capri.ui.theme import get_hud_font  # noqa: E402 # pylint: disable=wrong-import-position,wrong-import-order
