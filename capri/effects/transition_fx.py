"""Визуальные эффекты переходов: вортекс, телепортация, растворение и кибер-глитчи."""

from __future__ import annotations

import ctypes
import math
import random

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .transition_base import (
    BAYER_4X4,
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
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
    chamfer_points,
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
    "CyberPixelBolt",
    "CyberPixelSpark",
    "CyberShockwaveRing",
    "CyberTrailFragment",
    "DissolveTransitionOverlay",
    "ScreenTransitionOverlay",
    "ShardTransitionOverlay",
    "TeleportTransitionOverlay",
    "VortexTransitionOverlay",
    "chamfer_points",
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


def is_reduced_motion_enabled() -> bool:
    try:
        val = ctypes.c_bool()
        if ctypes.windll.user32.SystemParametersInfoW(
            0x1042, 0, ctypes.byref(val), 0
        ):
            return not val.value
    except Exception:
        pass
    return False


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


class CyberPixelBolt:
    """Пиксельный электрический разряд с процедурными ветвлениями."""

    def __init__(
        self,
        start: QPoint,
        end: QPoint,
        branch_chance: float = 0.30,
    ) -> None:
        self.start = snap_point(start)
        self.end = snap_point(end)
        self._branch_chance = max(0.0, min(1.0, branch_chance))
        self.segments: list[tuple[QPoint, QPoint]] = []
        self.branches: list[list[tuple[QPoint, QPoint]]] = []
        self.nodes: list[QPoint] = []
        self._energy_packet_pos = random.uniform(0.0, 1.0)
        self._rebuild()

    def _rebuild(self) -> None:
        self.segments.clear()
        self.branches.clear()
        self.nodes.clear()

        sx, sy = self.start.x(), self.start.y()
        ex, ey = self.end.x(), self.end.y()

        dx = ex - sx
        dy = ey - sy
        dist = math.hypot(dx, dy)
        if dist < PIXEL_SIZE * 2:
            return

        steps = max(5, min(20, int(dist // 26)))
        nx = -dy / dist
        ny = dx / dist

        offset = 0.0
        max_offset = min(70.0, max(18.0, dist * 0.22))
        prev = self.start
        key_points: list[QPoint] = [prev]

        for i in range(1, steps + 1):
            t = i / steps
            bx = sx + dx * t
            by = sy + dy * t

            offset += random.uniform(-1.0, 1.0) * max_offset * 0.55
            if random.random() < 0.18:
                offset += random.choice((-1.0, 1.0)) * max_offset * 0.9
            offset *= 0.58
            offset = max(-max_offset, min(max_offset, offset))

            px = snap_pixel(bx + nx * offset + random.uniform(-6.0, 6.0))
            py = snap_pixel(by + ny * offset + random.uniform(-6.0, 6.0))
            cur = QPoint(px, py)

            if i == steps:
                cur = QPoint(ex, ey)

            seg_dx = cur.x() - prev.x()
            seg_dy = cur.y() - prev.y()
            seg_len = math.hypot(seg_dx, seg_dy)
            if seg_len > 18 and random.random() < 0.75:
                if random.random() < 0.45:
                    step_x = prev.x() + int(
                        seg_dx * random.choice((0.3, 0.5, 0.7))
                    )
                    corner = QPoint(
                        snap_pixel(step_x), snap_pixel(prev.y())
                    )
                    self.segments.append((prev, corner))
                    self.segments.append((corner, cur))
                else:
                    mx = prev.x() + seg_dx * random.uniform(0.30, 0.70)
                    my = prev.y() + seg_dy * random.uniform(0.30, 0.70)
                    snx = -seg_dy / max(1.0, seg_len)
                    sny = seg_dx / max(1.0, seg_len)
                    kink = random.uniform(-18.0, 18.0)
                    mid = QPoint(
                        snap_pixel(mx + snx * kink),
                        snap_pixel(my + sny * kink),
                    )
                    self.segments.append((prev, mid))
                    self.segments.append((mid, cur))
            else:
                self.segments.append((prev, cur))

            key_points.append(cur)
            prev = cur

        forks = 0
        max_forks = max(1, int(steps * self._branch_chance))
        for i in range(1, len(key_points) - 2):
            if forks >= max_forks:
                break
            if random.random() < self._branch_chance:
                branch = self._build_branch(key_points[i], nx, ny, dist)
                if branch:
                    self.branches.append(branch)
                    forks += 1

    def _build_branch(
        self,
        origin: QPoint,
        main_nx: float,
        main_ny: float,
        main_dist: float,
    ) -> list[tuple[QPoint, QPoint]]:
        branch: list[tuple[QPoint, QPoint]] = []

        angle_sign = 1.0 if random.random() < 0.5 else -1.0
        base_angle = math.atan2(main_ny, main_nx)
        rad = base_angle + angle_sign * random.uniform(0.45, 1.15)
        branch_len = random.uniform(
            22.0, min(110.0, max(30.0, main_dist * 0.38))
        )
        steps = random.randint(2, 5)

        prev = origin
        for i in range(1, steps + 1):
            t = i / steps
            spread = branch_len * t
            jitter = random.uniform(-12.0, 12.0) * t
            px = snap_pixel(
                origin.x()
                + math.cos(rad) * spread
                + math.cos(rad + math.pi / 2) * jitter
            )
            py = snap_pixel(
                origin.y()
                + math.sin(rad) * spread
                + math.sin(rad + math.pi / 2) * jitter
            )
            cur = QPoint(px, py)
            branch.append((prev, cur))
            prev = cur
        return branch

    def jitter(self) -> None:

        if random.random() < 0.46:
            self._rebuild()

    def draw(self, painter: QPainter, progress: float) -> None:
        if not self.segments or progress <= 0:
            return

        visible_count = max(
            1, int(len(self.segments) * min(1.0, progress))
        )
        visible_segments = self.segments[:visible_count]
        visible_branches: list[tuple[QPoint, QPoint]] = []
        for branch in self.branches:
            b_count = max(1, int(len(branch) * min(1.0, progress * 1.35)))
            visible_branches.extend(branch[:b_count])

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        black_pen = QPen(with_alpha(COLOR_OBSIDIAN, 245), PIXEL_SIZE * 2)
        black_pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        black_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(black_pen)
        for p1, p2 in visible_segments:
            painter.drawLine(p1, p2)
        for p1, p2 in visible_branches:
            painter.drawLine(p1, p2)

        glow_pen = QPen(with_alpha(COLOR_CRIMSON, 70), PIXEL_SIZE * 3)
        glow_pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        glow_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(glow_pen)
        for p1, p2 in visible_segments:
            painter.drawLine(p1, p2)

        red_pen = QPen(COLOR_CRIMSON, PIXEL_SIZE)
        red_pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        red_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(red_pen)
        for p1, p2 in visible_segments:
            alpha = random.randint(185, 255)
            painter.setPen(
                QPen(with_alpha(COLOR_CRIMSON, alpha), PIXEL_SIZE)
            )
            painter.drawLine(p1, p2)

        core_pen = QPen(
            with_alpha(COLOR_WHITE, random.randint(190, 255)),
            max(1, PIXEL_SIZE // 2),
        )
        core_pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(core_pen)
        for p1, p2 in visible_segments:
            painter.drawLine(p1, p2)

        branch_black = QPen(with_alpha(COLOR_OBSIDIAN, 225), PIXEL_SIZE)
        branch_black.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(branch_black)
        for p1, p2 in visible_branches:
            painter.drawLine(p1, p2)
        branch_red = QPen(COLOR_CRIMSON, max(1, PIXEL_SIZE // 2))
        branch_red.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(branch_red)
        for p1, p2 in visible_branches:
            painter.drawLine(p1, p2)

        for endpoint, size in (
            (self.start, PIXEL_SIZE * 2),
            (self.end, PIXEL_SIZE),
        ):
            painter.fillRect(
                endpoint.x() - size // 2,
                endpoint.y() - size // 2,
                size,
                size,
                COLOR_CRIMSON,
            )
        painter.restore()



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
