from __future__ import annotations

import math
import random
from typing import List, Tuple

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen

# --- Константы пиксельного стиля ---
PIXEL_SIZE = 4

# Цвета глитчей (красный, розовый, чёрный, зелёный)
GLITCH_RED = (
    QColor(255, 0, 50),
    QColor(255, 30, 75),
    QColor(220, 0, 35),
    QColor(255, 60, 90),
)

GLITCH_PINK = (
    QColor(255, 45, 125),
    QColor(255, 0, 140),
    QColor(255, 105, 180),
    QColor(255, 70, 160),
)

GLITCH_BLACK = (
    QColor(0, 0, 0),
    QColor(8, 8, 12),
    QColor(16, 0, 8),
)

GLITCH_GREEN = (
    QColor(0, 255, 65),
    QColor(57, 255, 106),
    QColor(0, 230, 118),
    QColor(16, 255, 120),
)

ALL_GLITCH_COLORS = GLITCH_RED + GLITCH_PINK + GLITCH_BLACK + GLITCH_GREEN

# Цвета молний
LIGHTNING_PINK_HALO = QColor(255, 35, 125, 240)
LIGHTNING_PINK_GLOW = QColor(255, 0, 140, 180)
LIGHTNING_PINK_CORE = QColor(255, 235, 245, 255)

# Цвета вспышки
FLASH_RED_CORE = QColor(255, 0, 45)
FLASH_RED_GLOW = QColor(255, 20, 60)

# Длительности анимации (мс)
DURATION_OUT_MS = 680
DURATION_IN_MS = 560

# Матрица дизеринга Байера 4x4
BAYER_4X4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def snap_pixel(val: float | int, step: int = PIXEL_SIZE) -> int:
    """Привязка координаты к пиксельной сетке."""
    return int(val // step) * step


def perimeter_points(rect: QRect, count: int) -> List[QPoint]:
    """Случайные точки на периметре прямоугольника с пиксельным квантованием."""
    result: List[QPoint] = []
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


def edge_points(screen: QRect, count: int) -> List[QPoint]:
    """Случайные точки на краях экрана с пиксельным квантованием."""
    result: List[QPoint] = []
    for _ in range(count):
        side = random.randrange(4)
        if side == 0:
            x = snap_pixel(random.randint(screen.left(), screen.right()))
            y = snap_pixel(screen.top())
        elif side == 1:
            x = snap_pixel(screen.right())
            y = snap_pixel(random.randint(screen.top(), screen.bottom()))
        elif side == 2:
            x = snap_pixel(random.randint(screen.left(), screen.right()))
            y = snap_pixel(screen.bottom())
        else:
            x = snap_pixel(screen.left())
            y = snap_pixel(random.randint(screen.top(), screen.bottom()))
        result.append(QPoint(x, y))
    return result


class PixelSpark:
    """Пиксельная искра/осколок для вспышек и молний."""

    __slots__ = ("x", "y", "vx", "vy", "color", "size", "life", "max_life")

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: QColor,
        size: int,
        life: float,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life

    def step(self, dt: float) -> bool:
        self.life -= dt
        if self.life <= 0:
            return False
        self.x += self.vx * dt
        self.y += self.vy * dt
        return True

    def draw(self, painter: QPainter) -> None:
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        c = QColor(self.color)
        c.setAlpha(alpha)
        sx = snap_pixel(self.x)
        sy = snap_pixel(self.y)
        painter.fillRect(sx, sy, self.size, self.size, c)


class PixelLightningBolt:
    """Пиксельная молния со ступенчатым рендерингом и ветвлениями."""

    def __init__(self, start: QPoint, end: QPoint) -> None:
        self.start = start
        self.end = end
        self.segments: List[Tuple[QPoint, QPoint]] = []
        self.branches: List[List[Tuple[QPoint, QPoint]]] = []
        self._rebuild()

    def _rebuild(self) -> None:
        """Построение пиксельной ступенчатой траектории с джиттером."""
        self.segments.clear()
        self.branches.clear()

        sx, sy = self.start.x(), self.start.y()
        ex, ey = self.end.x(), self.end.y()
        dx = ex - sx
        dy = ey - sy
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return

        steps = max(5, int(dist // 28))
        nx = -dy / dist
        ny = dx / dist

        prev = QPoint(sx, sy)
        key_points: List[QPoint] = [prev]

        for i in range(1, steps):
            t = i / steps
            bx = sx + dx * t
            by = sy + dy * t
            jitter = random.uniform(-0.45, 0.45) * min(70.0, dist * 0.28)
            px = snap_pixel(bx + nx * jitter)
            py = snap_pixel(by + ny * jitter)
            cur = QPoint(px, py)
            key_points.append(cur)

        key_points.append(QPoint(ex, ey))

        # Ступенчатое соединение
        for i in range(len(key_points) - 1):
            p1 = key_points[i]
            p2 = key_points[i + 1]
            if random.random() < 0.5:
                mid = QPoint(snap_pixel(p2.x()), snap_pixel(p1.y()))
            else:
                mid = QPoint(snap_pixel(p1.x()), snap_pixel(p2.y()))
            self.segments.append((p1, mid))
            self.segments.append((mid, p2))

            # Генерация боковых ветвей
            if random.random() < 0.28 and i < len(key_points) - 2:
                branch = self._generate_branch(p2, dx, dy, dist)
                if branch:
                    self.branches.append(branch)

    def _generate_branch(
        self, origin: QPoint, main_dx: float, main_dy: float, main_dist: float
    ) -> List[Tuple[QPoint, QPoint]]:
        """Генерация короткой ступенчатой ветви, отходящей в сторону."""
        branch: List[Tuple[QPoint, QPoint]] = []
        angle_sign = 1 if random.random() < 0.5 else -1
        rad = math.atan2(main_dy, main_dx) + angle_sign * random.uniform(0.6, 1.1)
        branch_len = random.uniform(30.0, min(120.0, main_dist * 0.35))
        bx = origin.x() + math.cos(rad) * branch_len
        by = origin.y() + math.sin(rad) * branch_len

        cur = origin
        num_sub = max(2, int(branch_len // 22))
        for step in range(1, num_sub + 1):
            t = step / num_sub
            target_x = snap_pixel(
                origin.x() + (bx - origin.x()) * t + random.randint(-12, 12)
            )
            target_y = snap_pixel(
                origin.y() + (by - origin.y()) * t + random.randint(-12, 12)
            )
            nxt = QPoint(target_x, target_y)
            mid = QPoint(snap_pixel(nxt.x()), snap_pixel(cur.y()))
            branch.append((cur, mid))
            branch.append((mid, nxt))
            cur = nxt
        return branch

    def jitter(self) -> None:
        """Легкая вибрация молнии при каждом кадре."""
        if random.random() < 0.35:
            self._rebuild()

    def draw(self, painter: QPainter, progress: float) -> None:
        """Отрисовка пиксельной молнии."""
        if not self.segments or progress <= 0:
            return

        visible_count = max(1, int(len(self.segments) * min(1.0, progress)))

        # 1. Halo
        halo_pen = QPen(LIGHTNING_PINK_HALO, PIXEL_SIZE * 2)
        halo_pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        halo_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(halo_pen)
        for i in range(visible_count):
            p1, p2 = self.segments[i]
            painter.drawLine(p1, p2)

        for branch in self.branches:
            b_count = max(1, int(len(branch) * min(1.0, progress * 1.2)))
            for j in range(b_count):
                p1, p2 = branch[j]
                painter.drawLine(p1, p2)

        # 2. Core
        core_pen = QPen(LIGHTNING_PINK_CORE, PIXEL_SIZE)
        core_pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        core_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(core_pen)
        for i in range(visible_count):
            p1, p2 = self.segments[i]
            painter.drawLine(p1, p2)

        for branch in self.branches:
            b_count = max(1, int(len(branch) * min(1.0, progress * 1.2)))
            for j in range(b_count):
                p1, p2 = branch[j]
                painter.drawLine(p1, p2)
