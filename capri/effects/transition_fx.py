"""Визуальные эффекты переходов: вортекс, телепортация, растворение и кибер-глитчи."""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import QWidget

from ..integrations.system_control import is_reduced_motion_enabled
from .transition_base import (
    BAYER_4X4,
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    DURATION_DODGE_MS,
    DURATION_ERRATIC_MS,
    DURATION_IN_MS,
    DURATION_OUT_MS,
    DURATION_POINT_MS,
    PALETTE_COLORS,
    PALETTE_WEIGHTS,
    PIXEL_SIZE,
    pick_palette_color,
    snap_pixel,
    snap_point,
    with_alpha,
)
from .transition_painters import (
    CyberHoloReticle,
    CyberKiroshiReticle,
    CyberShockwaveRing,
    CyberTriggerCrosshair,
    draw_breach_grid,
    draw_glitch_text,
    draw_hazard_frame,
    draw_hex_stream,
    draw_quickhack_panel,
    draw_scan_sweep,
    draw_scanlines,
    draw_screen_glitch_bars,
)

__all__ = [
    "BAYER_4X4",
    "COLOR_ACID_GREEN",
    "COLOR_CRIMSON",
    "COLOR_ELECTRIC_BLUE",
    "COLOR_OBSIDIAN",
    "COLOR_VIOLET",
    "COLOR_WHITE",
    "DURATION_DODGE_MS",
    "DURATION_ERRATIC_MS",
    "DURATION_IN_MS",
    "DURATION_OUT_MS",
    "DURATION_POINT_MS",
    "PALETTE_COLORS",
    "PALETTE_WEIGHTS",
    "PIXEL_SIZE",
    "BlackwallBreachTransitionOverlay",
    "CyberHoloReticle",
    "CyberKiroshiReticle",
    "CyberPixelSpark",
    "CyberShockwaveRing",
    "CyberTrailFragment",
    "CyberTriggerCrosshair",
    "CyberVectorBolt",
    "DissolveTransitionOverlay",
    "ScreenTransitionOverlay",
    "ShardTransitionOverlay",
    "TeleportTransitionOverlay",
    "VortexTransitionOverlay",
    "draw_breach_grid",
    "draw_glitch_mass",
    "draw_glitch_text",
    "draw_hazard_frame",
    "draw_hex_stream",
    "draw_quickhack_panel",
    "draw_scan_sweep",
    "draw_scanlines",
    "draw_screen_glitch_bars",
    "evaluate_bezier",
    "evaluate_manhattan_path",
    "evaluate_vortex",
    "is_reduced_motion_enabled",
    "nearest_offscreen_point",
    "perimeter_circuit_points",
    "pick_palette_color",
    "random_offscreen_point",
    "snap_pixel",
    "snap_point",
    "with_alpha",
]








def perimeter_circuit_points(rect: QRect, count: int) -> list[QPoint]:

    result: list[QPoint] = []
    if rect.width() <= 0 or rect.height() <= 0:
        return result
    for _ in range(count):
        side = random.randrange(4)
        if side == 0:
            x = snap_pixel(random.randint(rect.left(), rect.right()))
            y = snap_pixel(rect.top())
        elif side == 1:
            x = snap_pixel(rect.right())
            y = snap_pixel(random.randint(rect.top(), rect.bottom()))
        elif side == 2:
            x = snap_pixel(random.randint(rect.left(), rect.right()))
            y = snap_pixel(rect.bottom())
        else:
            x = snap_pixel(rect.left())
            y = snap_pixel(random.randint(rect.top(), rect.bottom()))
        result.append(QPoint(x, y))
    return result


def random_offscreen_point(
    screen: QRect, target: QRect, margin: int = 70
) -> QPoint:
    side = random.choice(("top", "right", "bottom", "left"))
    if side == "top":
        x = random.randint(
            screen.left(),
            max(screen.left(), screen.right() - target.width()),
        )
        y = screen.top() - target.height() - margin
    elif side == "bottom":
        x = random.randint(
            screen.left(),
            max(screen.left(), screen.right() - target.width()),
        )
        y = screen.bottom() + margin
    elif side == "left":
        x = screen.left() - target.width() - margin
        y = random.randint(
            screen.top(),
            max(screen.top(), screen.bottom() - target.height()),
        )
    else:
        x = screen.right() + margin
        y = random.randint(
            screen.top(),
            max(screen.top(), screen.bottom() - target.height()),
        )
    return snap_point(QPoint(x, y))


def nearest_offscreen_point(
    screen: QRect, target: QRect, margin: int = 70
) -> QPoint:

    dist_top = target.top() - screen.top()
    dist_bottom = screen.bottom() - target.bottom()
    dist_left = target.left() - screen.left()
    dist_right = screen.right() - target.right()

    min_dist = min(dist_top, dist_bottom, dist_left, dist_right)

    if min_dist == dist_top:
        x = target.x()
        y = screen.top() - target.height() - margin
    elif min_dist == dist_bottom:
        x = target.x()
        y = screen.bottom() + margin
    elif min_dist == dist_left:
        x = screen.left() - target.width() - margin
        y = target.y()
    else:
        x = screen.right() + margin
        y = target.y()

    return snap_point(QPoint(x, y))


def evaluate_bezier(
    p0: QPoint, p1: QPoint, p2: QPoint, t: float
) -> QPoint:
    inv = 1.0 - t
    x = inv * inv * p0.x() + 2.0 * inv * t * p1.x() + t * t * p2.x()
    y = inv * inv * p0.y() + 2.0 * inv * t * p1.y() + t * t * p2.y()
    return QPoint(int(x), int(y))


def evaluate_manhattan_path(
    p0: QPoint, p2: QPoint, mid_t: float, t: float, orientation: int = 0
) -> QPoint:
    mid_x = int(p0.x() + (p2.x() - p0.x()) * mid_t)
    mid_y = int(p0.y() + (p2.y() - p0.y()) * mid_t)
    if orientation == 0:
        c1 = QPoint(mid_x, p0.y())
        c2 = QPoint(mid_x, p2.y())
    else:
        c1 = QPoint(p0.x(), mid_y)
        c2 = QPoint(p2.x(), mid_y)

    if t <= 0.33:
        sub_t = t / 0.33
        return QPoint(
            int(p0.x() + (c1.x() - p0.x()) * sub_t),
            int(p0.y() + (c1.y() - p0.y()) * sub_t),
        )
    if t <= 0.66:
        sub_t = (t - 0.33) / 0.33
        return QPoint(
            int(c1.x() + (c2.x() - c1.x()) * sub_t),
            int(c1.y() + (c2.y() - c1.y()) * sub_t),
        )
    sub_t = (t - 0.66) / 0.34
    return QPoint(
        int(c2.x() + (p2.x() - c2.x()) * sub_t),
        int(c2.y() + (p2.y() - c2.y()) * sub_t),
    )


def evaluate_vortex(
    p0: QPoint,
    p2: QPoint,
    t: float,
    spiral_turns: float,
    max_radius: float,
) -> QPoint:
    base_x = p0.x() + (p2.x() - p0.x()) * t
    base_y = p0.y() + (p2.y() - p0.y()) * t
    env = math.sin(t * math.pi)
    r = max_radius * env
    ang = t * math.tau * spiral_turns
    return QPoint(
        int(base_x + math.cos(ang) * r), int(base_y + math.sin(ang) * r)
    )


class CyberTrailFragment:
    """Фрагмент пиксельного шлейфа за перемещающимся объектом."""

    __slots__ = ("color", "h", "life", "max_life", "w", "x", "y")

    def __init__(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        color: QColor,
        life: float = 0.36,
    ) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.color = color
        self.life = life
        self.max_life = max(0.001, life)

    def step(self, dt: float) -> bool:
        self.life -= dt
        return self.life > 0.0

    def draw(self, painter: QPainter) -> None:
        if self.life <= 0.0:
            return
        ratio = max(0.0, min(1.0, self.life / self.max_life))
        alpha = int(self.color.alpha() * (ratio**1.5))
        if alpha <= 4:
            return
        painter.fillRect(
            self.x, self.y, self.w, self.h, with_alpha(self.color, alpha)
        )


def draw_glitch_mass(
    painter: QPainter,
    center: QPoint,
    base_size: int,
    intensity: float = 1.0,
    seed: int = 0,
) -> None:
    rnd = random.Random(seed)
    sz = max(PIXEL_SIZE * 3, snap_pixel(int(base_size)))
    half = sz // 2
    rect = QRect(center.x() - half, center.y() - half, sz, sz)

    painter.fillRect(rect, with_alpha(COLOR_OBSIDIAN, 220))

    shift = snap_pixel(int((2 + 6 * intensity) * rnd.choice((-1, 1))))
    shift_y = snap_pixel(int((1 + 3 * intensity) * rnd.choice((-1, 1))))
    painter.fillRect(
        rect.translated(shift, shift_y),
        with_alpha(COLOR_CRIMSON, int(150 * intensity)),
    )
    painter.fillRect(
        rect.translated(-shift, -shift_y),
        with_alpha(COLOR_ELECTRIC_BLUE, int(130 * intensity)),
    )
    painter.fillRect(
        rect.translated(shift // 2, -shift // 2),
        with_alpha(COLOR_ACID_GREEN, int(110 * intensity)),
    )

    slices = int(3 + 8 * intensity)
    for _ in range(slices):
        sy = rnd.randint(
            rect.top(), max(rect.top(), rect.bottom() - PIXEL_SIZE)
        )
        sh = snap_pixel(rnd.choice((PIXEL_SIZE, PIXEL_SIZE * 2)))
        sw = snap_pixel(rnd.randint(sz // 2, int(sz * 1.6)))
        sx = (
            center.x()
            - sw // 2
            + snap_pixel(int(rnd.randint(-12, 12) * intensity))
        )
        c = pick_palette_color()
        painter.fillRect(
            sx, sy, sw, sh, with_alpha(c, rnd.randint(160, 240))
        )

    bits = int(6 + 16 * intensity)
    for _ in range(bits):
        bx = center.x() + snap_pixel(
            int(rnd.randint(-half - 12, half + 12) * intensity)
        )
        by = center.y() + snap_pixel(
            int(rnd.randint(-half - 12, half + 12) * intensity)
        )
        bsz = snap_pixel(rnd.choice((PIXEL_SIZE, PIXEL_SIZE * 2)))
        painter.fillRect(
            bx,
            by,
            bsz,
            bsz,
            with_alpha(pick_palette_color(), rnd.randint(180, 255)),
        )

    painter.fillRect(
        center.x() - PIXEL_SIZE,
        center.y() - PIXEL_SIZE,
        PIXEL_SIZE * 2,
        PIXEL_SIZE * 2,
        COLOR_WHITE,
    )





class CyberPixelSpark:
    """Пиксельная искра для эффектов разрядов и динамических переходов."""

    __slots__ = (
        "color",
        "flicker_phase",
        "kind",
        "life",
        "max_life",
        "size",
        "vx",
        "vy",
        "x",
        "y",
    )

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: QColor | None = None,
        size: int = PIXEL_SIZE,
        life: float = 0.35,
        kind: str = "spark",
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color if color is not None else pick_palette_color()
        self.size = size
        self.life = life
        self.max_life = life
        self.kind = kind
        self.flicker_phase = random.uniform(0, math.tau)

    def step(self, dt: float) -> bool:
        self.life -= dt
        if self.life <= 0:
            return False

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.94
        self.vy *= 0.94
        self.flicker_phase += dt * 25.0
        return True

    def draw(self, painter: QPainter) -> None:
        if self.life <= 0:
            return
        ratio = self.life / self.max_life
        flicker = 0.75 + 0.25 * math.sin(self.flicker_phase)
        alpha = max(0, min(255, int(255 * ratio * flicker)))

        c = QColor(self.color)
        c.setAlpha(alpha)

        px = snap_pixel(self.x)
        py = snap_pixel(self.y)

        if self.kind == "bar":
            w = snap_pixel(self.size * 3)
            h = snap_pixel(self.size)
            painter.fillRect(px - w // 2, py, w, h, c)

            if ratio > 0.45 and self.color != COLOR_OBSIDIAN:
                wc = QColor(COLOR_WHITE)
                wc.setAlpha(int(alpha * 0.8))
                painter.fillRect(px - self.size // 2, py, self.size, h, wc)
        elif self.kind == "bit":
            painter.fillRect(px, py, self.size, self.size, c)
            if self.size >= PIXEL_SIZE * 2:
                void_color = QColor(COLOR_OBSIDIAN)
                void_color.setAlpha(int(alpha * 0.9))
                painter.fillRect(
                    px + PIXEL_SIZE // 2,
                    py + PIXEL_SIZE // 2,
                    self.size - PIXEL_SIZE,
                    self.size - PIXEL_SIZE,
                    void_color,
                )
        else:
            painter.fillRect(px, py, self.size, self.size, c)


class CyberVectorBolt:
    """Векторная монолитная молния переменной ширины в стиле Studio Trigger."""

    def __init__(
        self,
        start: QPoint | QPointF,
        end: QPoint | QPointF,
        base_width: float = 20.0,
        tip_width: float = 2.0,
        branch_chance: float = 0.25,
        color: QColor | None = None,
    ) -> None:
        self.start = QPointF(start)
        self.end = QPointF(end)
        self.base_width = max(4.0, float(base_width))
        self.tip_width = max(0.5, float(tip_width))
        self.branch_chance = max(0.0, min(1.0, branch_chance))
        self.color = color or COLOR_CRIMSON

        self.spine_points: list[QPointF] = []
        self.polygon = QPolygonF()
        self.ghost_polygon = QPolygonF()
        self.core_spine: list[QPointF] = []
        self.branches: list[QPolygonF] = []
        self._rebuild()

    def _rebuild(self) -> None:
        self.ghost_polygon = QPolygonF(self.polygon)
        self.spine_points.clear()
        self.polygon.clear()
        self.core_spine.clear()
        self.branches.clear()

        sx, sy = self.start.x(), self.start.y()
        ex, ey = self.end.x(), self.end.y()
        dx = ex - sx
        dy = ey - sy
        dist = math.hypot(dx, dy)
        if dist < 4.0:
            return

        # Направляющий вектор и нормаль
        ux = dx / dist
        uy = dy / dist
        nx = -uy
        ny = ux

        # Количество основных изломов (3-5 для фирменного аниме-зигзага)
        steps = max(3, min(6, int(dist // 70) + 1))
        pts: list[QPointF] = [self.start]

        # Чередование направления изломов для резкого зигзага (как в референсе)
        kink_sign = 1.0 if random.random() < 0.5 else -1.0
        max_offset = min(65.0, max(14.0, dist * 0.18))

        for i in range(1, steps):
            ratio = i / steps
            bx = sx + dx * ratio
            by = sy + dy * ratio

            offset = kink_sign * random.uniform(max_offset * 0.65, max_offset)
            pts.append(QPointF(bx + nx * offset, by + ny * offset))
            kink_sign *= -1.0

        pts.append(self.end)
        self.spine_points = pts
        self.core_spine = list(pts)

        # Построение контура полигона переменной ширины (tapering: от base_width к tip_width)
        left_side: list[QPointF] = []
        right_side: list[QPointF] = []

        n_pts = len(pts)
        for i, pt in enumerate(pts):
            t = i / max(1, n_pts - 1)
            half_w = (self.base_width * (1.0 - t) + self.tip_width * t) * 0.5

            # Усредненная нормаль на стыке сегментов
            if i == 0:
                seg_dx = pts[1].x() - pt.x()
                seg_dy = pts[1].y() - pt.y()
            elif i == n_pts - 1:
                seg_dx = pt.x() - pts[i - 1].x()
                seg_dy = pt.y() - pts[i - 1].y()
            else:
                seg_dx = pts[i + 1].x() - pts[i - 1].x()
                seg_dy = pts[i + 1].y() - pts[i - 1].y()

            seg_len = math.hypot(seg_dx, seg_dy) or 1.0
            p_nx = -seg_dy / seg_len
            p_ny = seg_dx / seg_len

            left_side.append(QPointF(pt.x() + p_nx * half_w, pt.y() + p_ny * half_w))
            right_side.append(QPointF(pt.x() - p_nx * half_w, pt.y() - p_ny * half_w))

        # Собираем замкнутый полигон: по левой стороне вперед, по правой назад
        full_pts = left_side + list(reversed(right_side))
        self.polygon = QPolygonF(full_pts)

        # Генерация боковых клиновидных отростков
        if self.branch_chance > 0.05 and n_pts >= 3:
            for b_idx in range(1, n_pts - 1):
                if random.random() < self.branch_chance:
                    b_poly = self._create_branch_polygon(pts[b_idx], ux, uy, dist)
                    if b_poly and not b_poly.isEmpty():
                        self.branches.append(b_poly)

    def _create_branch_polygon(
        self,
        origin: QPointF,
        ux: float,
        uy: float,
        total_dist: float,
    ) -> QPolygonF:
        side = 1.0 if random.random() < 0.5 else -1.0
        angle = math.atan2(uy, ux) + side * random.uniform(0.6, 1.2)
        b_len = random.uniform(25.0, min(120.0, total_dist * 0.4))
        kink = random.uniform(-15.0, 15.0)

        mid_x = origin.x() + math.cos(angle) * (b_len * 0.5) + math.cos(angle + math.pi / 2) * kink
        mid_y = origin.y() + math.sin(angle) * (b_len * 0.5) + math.sin(angle + math.pi / 2) * kink
        tip_x = origin.x() + math.cos(angle) * b_len
        tip_y = origin.y() + math.sin(angle) * b_len

        w_b = self.base_width * 0.45
        b_nx = -math.sin(angle)
        b_ny = math.cos(angle)

        return QPolygonF([
            QPointF(origin.x() + b_nx * w_b, origin.y() + b_ny * w_b),
            QPointF(mid_x + b_nx * (w_b * 0.4), mid_y + b_ny * (w_b * 0.4)),
            QPointF(tip_x, tip_y),
            QPointF(mid_x - b_nx * (w_b * 0.4), mid_y - b_ny * (w_b * 0.4)),
            QPointF(origin.x() - b_nx * w_b, origin.y() - b_ny * w_b),
        ])

    def jitter(self, force: bool = False) -> None:
        if force or random.random() < 0.65:
            self._rebuild()

    def draw(self, painter: QPainter, progress: float = 1.0) -> None:
        if progress <= 0.0 or self.polygon.isEmpty():
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        alpha_val = int(255 * min(1.0, progress))

        # 1. Призрачный остаточный фантом (ghost motion trail) со сдвигом
        if not self.ghost_polygon.isEmpty():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(with_alpha(self.color, int(alpha_val * 0.35)))
            painter.drawPolygon(self.ghost_polygon)

        # 2. Основное монолитное тело молнии
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(with_alpha(self.color, alpha_val))
        painter.drawPolygon(self.polygon)

        # 3. Боковые отростки (если включены)
        for b_poly in self.branches:
            painter.drawPolygon(b_poly)

        painter.restore()


class CyberPixelBolt(CyberVectorBolt):
    """Адаптер обратной совместимости для старых вызовов."""

    def __init__(
        self,
        start: QPoint | QPointF,
        end: QPoint | QPointF,
        branch_chance: float = 0.30,
        **kwargs: object,
    ) -> None:
        super().__init__(start, end, branch_chance=branch_chance, **kwargs)  # type: ignore[arg-type]


class ScreenTransitionOverlay(QWidget):
    """Базовый полноэкранный оверлей визуальных переходов."""

    finished = Signal()


class VortexTransitionOverlay(ScreenTransitionOverlay):
    """Оверлей перехода с вихревой траекторией перемещения."""


class TeleportTransitionOverlay(ScreenTransitionOverlay):
    """Оверлей перехода с эффектом мгновенной телепортации."""


class DissolveTransitionOverlay(ScreenTransitionOverlay):
    """Оверлей перехода с эффектом пиксельного растворения."""


class ShardTransitionOverlay(ScreenTransitionOverlay):
    """Оверлей перехода с разлетом на цифровые осколки."""


class BlackwallBreachTransitionOverlay(ScreenTransitionOverlay):
    """Оверлей перехода с эффектом кибер-пробоя Blackwall."""
