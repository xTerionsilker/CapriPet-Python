from __future__ import annotations

import random
from dataclasses import dataclass

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap

from capri.ui.theme import get_hud_font
from ..effects.transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
    PIXEL_SIZE,
    pick_palette_color,
    snap_pixel,
)

GAP = 24
OVERLAP_ATTEMPTS = 200

def free_bands(area: QRect, blocked: QRect | None) -> list[QRect]:
    if blocked is None or blocked.isEmpty():
        return [area]

    bands: list[QRect] = []
    if blocked.top() > area.top():
        bands.append(
            QRect(
                area.left(),
                area.top(),
                area.width(),
                blocked.top() - area.top(),
            )
        )
    if blocked.bottom() < area.bottom():
        bands.append(
            QRect(
                area.left(),
                blocked.bottom() + 1,
                area.width(),
                area.bottom() - blocked.bottom(),
            )
        )
    if blocked.left() > area.left():
        bands.append(
            QRect(
                area.left(),
                area.top(),
                blocked.left() - area.left(),
                area.height(),
            )
        )
    if blocked.right() < area.right():
        bands.append(
            QRect(
                blocked.right() + 1,
                area.top(),
                area.right() - blocked.right(),
                area.height(),
            )
        )
    return bands

def random_free_point(
    bands: list[QRect], width: int, height: int
) -> tuple[int, int] | None:
    fitting = [
        band
        for band in bands
        if band.width() >= width and band.height() >= height
    ]
    if not fitting:
        return None

    spans = [
        (band, (band.width() - width + 1) * (band.height() - height + 1))
        for band in fitting
    ]
    choice = random.randrange(sum(span for _, span in spans))
    for band, span in spans:
        if choice < span:
            columns = band.width() - width + 1
            return (
                band.left() + choice % columns,
                band.top() + choice // columns,
            )
        choice -= span
    return None

def least_overlap_point(
    area: QRect, blocked: QRect, width: int, height: int
) -> tuple[int, int]:
    max_x = max(area.left(), area.right() - width + 1)
    max_y = max(area.top(), area.bottom() - height + 1)
    best = (area.left(), area.top())
    least_overlap: int | None = None
    for _ in range(OVERLAP_ATTEMPTS):
        x = random.randint(area.left(), max_x)
        y = random.randint(area.top(), max_y)
        overlap = QRect(x, y, width, height).intersected(blocked)
        overlap_area = overlap.width() * overlap.height()
        if least_overlap is None or overlap_area < least_overlap:
            least_overlap = overlap_area
            best = (x, y)
    return best

def pick_position(
    area: QRect, blocked: QRect | None, width: int, height: int
) -> tuple[int, int]:
    point = random_free_point(free_bands(area, blocked), width, height)
    if point is not None:
        return point
    if blocked is not None and not blocked.isEmpty():
        return least_overlap_point(area, blocked, width, height)
    return area.left(), area.top()

def pick_adjacent_position(
    area: QRect,
    target: QRect,
    width: int,
    height: int,
    gap: int = GAP,
    preferred_side: str | None = None,
    margin: int = 12,
) -> tuple[int, int, str]:
    safe_left = area.left() + margin
    safe_right = area.right() - margin
    safe_top = area.top() + margin
    safe_bottom = area.bottom() - margin

    rx = target.right() + gap
    ry = target.center().y() - height // 2
    ry_clamped = max(safe_top, min(ry, safe_bottom - height))
    right_rect = QRect(rx, ry_clamped, width, height)
    fits_right = (rx + width <= safe_right) and not right_rect.intersects(target)

    lx = target.left() - gap - width
    ly = target.center().y() - height // 2
    ly_clamped = max(safe_top, min(ly, safe_bottom - height))
    left_rect = QRect(lx, ly_clamped, width, height)
    fits_left = (lx >= safe_left) and not left_rect.intersects(target)

    tx = target.center().x() - width // 2
    tx_clamped = max(safe_left, min(tx, safe_right - width))
    ty = target.top() - gap - height
    top_rect = QRect(tx_clamped, ty, width, height)
    fits_top = (ty >= safe_top) and not top_rect.intersects(target)

    bx = target.center().x() - width // 2
    bx_clamped = max(safe_left, min(bx, safe_right - width))
    by = target.bottom() + gap
    bottom_rect = QRect(bx_clamped, by, width, height)
    fits_bottom = (by + height <= safe_bottom) and not bottom_rect.intersects(target)

    candidates: dict[str, tuple[int, int, bool, QRect]] = {
        "right": (rx, ry_clamped, fits_right, right_rect),
        "left": (lx, ly_clamped, fits_left, left_rect),
        "top": (tx_clamped, ty, fits_top, top_rect),
        "bottom": (bx_clamped, by, fits_bottom, bottom_rect),
    }

    if preferred_side and preferred_side in candidates and candidates[preferred_side][2]:
        x, y, _, _ = candidates[preferred_side]
        return x, y, preferred_side

    space_right = max(0, safe_right - target.right() - gap)
    space_left = max(0, target.left() - safe_left - gap)

    if space_right >= space_left:
        ordered_sides = ["right", "left", "top", "bottom"]
    else:
        ordered_sides = ["left", "right", "top", "bottom"]

    for side in ordered_sides:
        x, y, fits, _ = candidates[side]
        if fits:
            return x, y, side

    best_side = ordered_sides[0]
    best_overlap = float("inf")
    best_x, best_y = candidates[best_side][0], candidates[best_side][1]

    for side in ("right", "left", "top", "bottom"):
        cand_x, cand_y, _, _ = candidates[side]
        clamped_x = max(safe_left, min(cand_x, safe_right - width))
        clamped_y = max(safe_top, min(cand_y, safe_bottom - height))
        clamped_rect = QRect(clamped_x, clamped_y, width, height)
        overlap = clamped_rect.intersected(target)
        overlap_area = overlap.width() * overlap.height() if not overlap.isEmpty() else 0
        if overlap_area < best_overlap:
            best_overlap = overlap_area
            best_side = side
            best_x, best_y = clamped_x, clamped_y

    return best_x, best_y, best_side

def pick_side_position(
    area: QRect, target: QRect, width: int, height: int, gap: int = GAP
) -> tuple[int, int]:
    x, y, _ = pick_adjacent_position(area, target, width, height, gap=gap)
    return x, y

@dataclass
class PetRenderState:
    
    is_spawning: bool = False
    is_dragging: bool = False
    is_pose_transition: bool = False
    is_surge: bool = False
    is_speaking: bool = False
    telemetry_tag: str = "[CAPRI//ONLINE]"

class PetRenderer:
    

    def render(
        self,
        painter: QPainter,
        pixmap: QPixmap,
        state: PetRenderState,
    ) -> None:
        
        w = pixmap.width()
        h = pixmap.height()
        if w <= 0 or h <= 0 or pixmap.isNull():
            return

        severity = self._calculate_severity(state)

        shake_x = 0
        shake_y = 0
        if state.is_dragging:
            shake_x = random.choice((-4, -2, 0, 2, 4))
            shake_y = random.choice((-3, -1, 0, 1, 3))
            painter.translate(shake_x, shake_y)

        self._draw_blackwall_aura(painter, pixmap, w, h, severity)

        self._draw_chromatic_aberration(painter, pixmap, severity)

        self._draw_sliced_pixmap(painter, pixmap, w, h, severity)

        self._draw_silhouette_glitches(painter, w, h, severity, state.is_pose_transition)

        self._draw_sparks(painter, w, h, severity)

        self._draw_hud_telemetry(painter, w, h, severity, state)

        if state.is_dragging and (shake_x != 0 or shake_y != 0):
            painter.translate(-shake_x, -shake_y)

    def _draw_blackwall_aura(
        self, painter: QPainter, pixmap: QPixmap, w: int, h: int, severity: float
    ) -> None:
        echo_count = 3 if severity > 0.6 else (2 if severity > 0.3 else 2)
        step_base = 8 if severity > 0.6 else (5 if severity > 0.3 else 3)

        for i in range(echo_count):
            dx = snap_pixel(random.choice((-1, 1)) * (i + 1) * step_base)
            dy = snap_pixel(random.choice((-1, 0, 1)) * (i + 1) * max(2, step_base // 2))
            alpha = (
                random.randint(120, 190)
                if severity > 0.6
                else (random.randint(80, 140) if severity > 0.3 else random.randint(55, 95))
            )
            color = COLOR_CRIMSON if random.random() < 0.8 else COLOR_OBSIDIAN

            tinted = QPixmap(pixmap.size())
            tinted.fill(Qt.GlobalColor.transparent)
            p = QPainter()
            if p.begin(tinted):
                p.drawPixmap(0, 0, pixmap)
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                c = QColor(color)
                c.setAlpha(alpha)
                p.fillRect(tinted.rect(), c)
                p.end()

            painter.save()
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            painter.drawPixmap(dx, dy, tinted)
            painter.restore()

        tear_n = random.randint(3, 7) if severity > 0.6 else (random.randint(2, 4) if severity > 0.3 else random.randint(1, 2))
        for _ in range(tear_n):
            tw = snap_pixel(random.randint(w // 5, w // 2))
            th = snap_pixel(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)))
            tx = snap_pixel(random.randint(-12, max(0, w - tw + 12)))
            ty = snap_pixel(random.randint(0, max(0, h - th)))
            t_color = QColor(COLOR_CRIMSON if random.random() < 0.7 else COLOR_OBSIDIAN)
            t_color.setAlpha(random.randint(50, 120) if severity > 0.5 else random.randint(25, 60))
            painter.fillRect(tx, ty, tw, th, t_color)

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

            painter.save()
            painter.setOpacity(random.uniform(0.25, 0.45))
            painter.drawPixmap(-chroma_shift, 0, pixmap)
            painter.restore()

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

        scan_alpha = (
            random.randint(25, 60) if severity > 0.4 else random.randint(15, 35)
        )
        scan_color = QColor(COLOR_OBSIDIAN)
        scan_color.setAlpha(scan_alpha)
        painter.setPen(QPen(scan_color, 1))
        for y in range(0, h, PIXEL_SIZE):
            painter.drawLine(0, y, w, y)

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

        if severity > 0.5 and random.random() < 0.7:
            font = get_hud_font(10, bold=True)
            painter.setFont(font)
            glyph = random.choice(("01", "FA", "ERR", "0x4F", "TX", "99%"))
            gx = snap_pixel(random.randint(w // 4, max(w // 4 + 1, 3 * w // 4)))
            gy = snap_pixel(random.randint(h // 4, max(h // 4 + 1, 3 * h // 4)))
            painter.setPen(
                QColor(COLOR_ACID_GREEN if random.random() < 0.6 else COLOR_WHITE)
            )
            painter.drawText(gx, gy, glyph)

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
            font = get_hud_font(9, bold=True)
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
