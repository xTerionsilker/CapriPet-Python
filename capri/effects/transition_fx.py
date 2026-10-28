from __future__ import annotations

import math
import random
from typing import List, Tuple

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen

# --- Пиксельные константы ---
PIXEL_SIZE = 4

# --- Фирменная киберпанк-палитра Капри с процентным распределением ---
# #F20D2E (45%)  - Доминантный неоновый алый
# #0B0B0B (35%)  - Глубокий обсидиан / цифровой вакуум
# #3CF12B (16%)  - Кислотный кибер-зелёный
# #FFFFFF (2%)   - Ослепительное белое ядро перегрузки
# #1E70F0 (1.5%) - Высоковольтный синий
# #9922EE (0.5%) - Редкий неоновый ультрафиолет

COLOR_CRIMSON = QColor("#F20D2E")
COLOR_OBSIDIAN = QColor("#0B0B0B")
COLOR_ACID_GREEN = QColor("#3CF12B")
COLOR_WHITE = QColor("#FFFFFF")
COLOR_ELECTRIC_BLUE = QColor("#1E70F0")
COLOR_VIOLET = QColor("#9922EE")

PALETTE_COLORS = (
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_ACID_GREEN,
    COLOR_WHITE,
    COLOR_ELECTRIC_BLUE,
    COLOR_VIOLET,
)

PALETTE_WEIGHTS = (45.0, 35.0, 16.0, 2.0, 1.5, 0.5)


def pick_palette_color() -> QColor:
    """Выбирает случайный цвет с точным соблюдением процентного распределения палитры Капри."""
    return random.choices(PALETTE_COLORS, weights=PALETTE_WEIGHTS, k=1)[0]


# Длительность переходов (мс)
DURATION_OUT_MS = 640
DURATION_IN_MS = 560
DURATION_POINT_MS = 500

# Матрица дизеринга Байера 4x4
BAYER_4X4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def snap_pixel(val: float | int, step: int = PIXEL_SIZE) -> int:
    """Привязка значения к пиксельной сетке."""
    return int(val // step) * step


def snap_point(pt: QPoint, step: int = PIXEL_SIZE) -> QPoint:
    return QPoint(snap_pixel(pt.x(), step), snap_pixel(pt.y(), step))


def perimeter_circuit_points(rect: QRect, count: int) -> List[QPoint]:
    """Генерирует узловые точки на периметре с выравниванием по пиксельной сетке."""
    result: List[QPoint] = []
    if rect.width() <= 0 or rect.height() <= 0:
        return result
    for _ in range(count):
        side = random.randrange(4)
        if side == 0:  # Top
            x = snap_pixel(random.randint(rect.left(), rect.right()))
            y = snap_pixel(rect.top())
        elif side == 1:  # Right
            x = snap_pixel(rect.right())
            y = snap_pixel(random.randint(rect.top(), rect.bottom()))
        elif side == 2:  # Bottom
            x = snap_pixel(random.randint(rect.left(), rect.right()))
            y = snap_pixel(rect.bottom())
        else:  # Left
            x = snap_pixel(rect.left())
            y = snap_pixel(random.randint(rect.top(), rect.bottom()))
        result.append(QPoint(x, y))
    return result


def screen_bus_points(screen: QRect, count: int) -> List[QPoint]:
    """Точки ввода/вывода на границах экрана для цифровых шин."""
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


class CyberPixelSpark:
    """
    Пиксельная частица киберпанка: искры, биты данных и горизонтальные световые полоски,
    распределенные строго по палитре Капри.
    """

    __slots__ = (
        "x",
        "y",
        "vx",
        "vy",
        "color",
        "size",
        "life",
        "max_life",
        "kind",
        "flicker_phase",
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
        kind: str = "spark",  # "spark", "bit", "bar"
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
        # Дискретное движение с сопротивлением цифровой среды
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
            # Если полоска алая или зеленая — подсвечиваем белым субпикселем
            if ratio > 0.45 and self.color != COLOR_OBSIDIAN:
                wc = QColor(COLOR_WHITE)
                wc.setAlpha(int(alpha * 0.8))
                painter.fillRect(px - self.size // 2, py, self.size, h, wc)
        elif self.kind == "bit":
            # Квадратный блок бита (4x4 или 8x8)
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
            # Обычная пиксельная искра
            painter.fillRect(px, py, self.size, self.size, c)


class CyberPixelBolt:
    """
    Кибер-разряд: строго ортогональная (Манхэттенская) геометрия + 45° диагонали,
    узловые микрочипы (Arc Nodes) и бегущие энергетические пакеты данных.
    Выполнен в фирменной палитре Капри (#F20D2E 45%, #0B0B0B 35%, #3CF12B 16%).
    """

    def __init__(
        self,
        start: QPoint,
        end: QPoint,
        color_scheme: str = "crimson",  # "crimson" или "green"
    ) -> None:
        self.start = snap_point(start)
        self.end = snap_point(end)
        self.color_scheme = color_scheme
        self.segments: List[Tuple[QPoint, QPoint]] = []
        self.branches: List[List[Tuple[QPoint, QPoint]]] = []
        self.nodes: List[QPoint] = []
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

        steps = max(3, min(14, int(dist // 45)))
        nx = -dy / dist
        ny = dx / dist

        prev = QPoint(sx, sy)
        key_points: List[QPoint] = [prev]

        for i in range(1, steps):
            t = i / steps
            bx = sx + dx * t
            by = sy + dy * t
            jitter_dist = min(60.0, dist * 0.25)
            offset = random.choice((-1.0, -0.5, 0.0, 0.5, 1.0)) * jitter_dist
            px = snap_pixel(bx + nx * offset)
            py = snap_pixel(by + ny * offset)
            cur = QPoint(px, py)
            key_points.append(cur)

        key_points.append(QPoint(ex, ey))

        for i in range(len(key_points) - 1):
            p1 = key_points[i]
            p2 = key_points[i + 1]

            diag_len = min(abs(p2.x() - p1.x()), abs(p2.y() - p1.y()))
            if diag_len > PIXEL_SIZE * 4 and random.random() < 0.45:
                sign_x = 1 if p2.x() > p1.x() else -1
                sign_y = 1 if p2.y() > p1.y() else -1
                diag_pt = QPoint(
                    snap_pixel(p1.x() + sign_x * diag_len),
                    snap_pixel(p1.y() + sign_y * diag_len),
                )
                self.segments.append((p1, diag_pt))
                self.segments.append((diag_pt, p2))
                self.nodes.append(diag_pt)
            else:
                if random.random() < 0.5:
                    corner = QPoint(snap_pixel(p2.x()), snap_pixel(p1.y()))
                else:
                    corner = QPoint(snap_pixel(p1.x()), snap_pixel(p2.y()))
                self.segments.append((p1, corner))
                self.segments.append((corner, p2))
                self.nodes.append(corner)

            if random.random() < 0.30 and i < len(key_points) - 2:
                branch = self._build_branch(p2, dx, dy, dist)
                if branch:
                    self.branches.append(branch)

    def _build_branch(
        self, origin: QPoint, main_dx: float, main_dy: float, main_dist: float
    ) -> List[Tuple[QPoint, QPoint]]:
        branch: List[Tuple[QPoint, QPoint]] = []
        angle_sign = 1 if random.random() < 0.5 else -1
        rad = math.atan2(main_dy, main_dx) + angle_sign * random.choice(
            (math.pi / 2, math.pi / 4)
        )
        branch_len = snap_pixel(random.uniform(24.0, min(90.0, main_dist * 0.35)))

        end_x = snap_pixel(origin.x() + math.cos(rad) * branch_len)
        end_y = snap_pixel(origin.y() + math.sin(rad) * branch_len)
        target = QPoint(end_x, end_y)

        corner = QPoint(snap_pixel(target.x()), snap_pixel(origin.y()))
        branch.append((origin, corner))
        branch.append((corner, target))
        return branch

    def jitter(self) -> None:
        self._energy_packet_pos = (self._energy_packet_pos + 0.12) % 1.0
        if random.random() < 0.30:
            self._rebuild()

    def draw(self, painter: QPainter, progress: float) -> None:
        if not self.segments or progress <= 0:
            return

        visible_count = max(1, int(len(self.segments) * min(1.0, progress)))

        # Цвета в зависимости от схемы
        if self.color_scheme == "green":
            primary_color = COLOR_ACID_GREEN
            aberration_color = COLOR_CRIMSON
            sub_packet_color = COLOR_CRIMSON
        else:
            primary_color = COLOR_CRIMSON
            aberration_color = COLOR_ACID_GREEN
            sub_packet_color = COLOR_ACID_GREEN

        # Слой 1: Темная обсидиановая подложка (#0B0B0B, толщина 8px) для резкого кибер-контраста
        obsidian_pen = QPen(QColor(COLOR_OBSIDIAN.red(), COLOR_OBSIDIAN.green(), COLOR_OBSIDIAN.blue(), 190), PIXEL_SIZE * 2)
        obsidian_pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        obsidian_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(obsidian_pen)
        for i in range(visible_count):
            p1, p2 = self.segments[i]
            painter.drawLine(p1, p2)

        # Слой 2: Хроматическая аберрация (сдвинутый на 2px шлейф)
        ab_pen = QPen(QColor(aberration_color.red(), aberration_color.green(), aberration_color.blue(), 130), PIXEL_SIZE)
        ab_pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(ab_pen)
        for i in range(visible_count):
            p1, p2 = self.segments[i]
            painter.drawLine(p1.x() + 2, p1.y(), p2.x() + 2, p2.y())

        # Слой 3: Основное неоновое тело разряда (#F20D2E или #3CF12B, толщина 6px)
        neon_glow = QColor(primary_color)
        neon_glow.setAlpha(235)
        glow_pen = QPen(neon_glow, PIXEL_SIZE + 2)
        glow_pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        glow_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(glow_pen)
        for i in range(visible_count):
            p1, p2 = self.segments[i]
            painter.drawLine(p1, p2)

        for branch in self.branches:
            b_count = max(1, int(len(branch) * min(1.0, progress * 1.3)))
            for j in range(b_count):
                p1, p2 = branch[j]
                painter.drawLine(p1, p2)

        # Слой 4: Ослепительное белое ядро (#FFFFFF 2%, толщина 4px)
        core_pen = QPen(COLOR_WHITE, PIXEL_SIZE)
        core_pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        core_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(core_pen)
        for i in range(visible_count):
            p1, p2 = self.segments[i]
            painter.drawLine(p1, p2)

        for branch in self.branches:
            b_count = max(1, int(len(branch) * min(1.0, progress * 1.3)))
            for j in range(b_count):
                p1, p2 = branch[j]
                painter.drawLine(p1, p2)

        # Слой 5: Узловые диоды на изломах (Arc Nodes)
        for node in self.nodes[: visible_count // 2]:
            node_sz = PIXEL_SIZE * 2
            nx = node.x() - node_sz // 2
            ny = node.y() - node_sz // 2
            painter.fillRect(nx, ny, node_sz, node_sz, primary_color)
            painter.fillRect(
                nx + PIXEL_SIZE // 2,
                ny + PIXEL_SIZE // 2,
                PIXEL_SIZE,
                PIXEL_SIZE,
                COLOR_WHITE,
            )

        # Слой 6: Бегущий энергетический пакет данных (Data Energy Pulse)
        if visible_count > 0:
            target_idx = int(self._energy_packet_pos * (visible_count - 1))
            seg = self.segments[target_idx]
            pulse_x = snap_pixel((seg[0].x() + seg[1].x()) // 2)
            pulse_y = snap_pixel((seg[0].y() + seg[1].y()) // 2)
            pulse_sz = PIXEL_SIZE * 3

            # Обсидиановая рамка пакета
            painter.fillRect(
                pulse_x - pulse_sz // 2 - 2,
                pulse_y - pulse_sz // 2 - 2,
                pulse_sz + 4,
                pulse_sz + 4,
                COLOR_OBSIDIAN,
            )
            painter.fillRect(
                pulse_x - pulse_sz // 2,
                pulse_y - pulse_sz // 2,
                pulse_sz,
                pulse_sz,
                sub_packet_color,
            )
            # Белая центральная точка
            painter.fillRect(
                pulse_x - PIXEL_SIZE // 2,
                pulse_y - PIXEL_SIZE // 2,
                PIXEL_SIZE,
                PIXEL_SIZE,
                COLOR_WHITE,
            )


class CyberHoloReticle:
    """
    Кибернетический голографический прицел захвата цели / точки появления.
    Отрисовывает угловые скобки `[ + ]`, координатные риски и радарные маркеры
    в палитре Капри (#F20D2E и #3CF12B с контрастом #0B0B0B).
    """

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
            -bracket_offset, -bracket_offset, bracket_offset, bracket_offset
        )
        l, r, t, b = box.left(), box.right(), box.top(), box.bottom()

        painter.setPen(Qt.PenStyle.NoPen)
        alpha = max(0, min(255, int(255 * progress)))
        base_color = color if color is not None else COLOR_CRIMSON
        c = QColor(base_color)
        c.setAlpha(alpha)

        obsidian = QColor(COLOR_OBSIDIAN)
        obsidian.setAlpha(int(alpha * 0.95))

        # Обсидиановая контрастная тень для идеальной читаемости
        sh = 2
        for ox, oy in ((-sh, 0), (sh, 0), (0, -sh), (0, sh)):
            painter.fillRect(l + ox, t + oy, corner_len, thickness, obsidian)
            painter.fillRect(l + ox, t + oy, thickness, corner_len, obsidian)
            painter.fillRect(r - corner_len + 1 + ox, t + oy, corner_len, thickness, obsidian)
            painter.fillRect(r - thickness + 1 + ox, t + oy, thickness, corner_len, obsidian)
            painter.fillRect(l + ox, b - thickness + 1 + oy, corner_len, thickness, obsidian)
            painter.fillRect(l + ox, b - corner_len + 1 + oy, thickness, corner_len, obsidian)
            painter.fillRect(r - corner_len + 1 + ox, b - thickness + 1 + oy, corner_len, thickness, obsidian)
            painter.fillRect(r - thickness + 1 + ox, b - corner_len + 1 + oy, thickness, corner_len, obsidian)

        # 1. Верхний левый угол
        painter.fillRect(l, t, corner_len, thickness, c)
        painter.fillRect(l, t, thickness, corner_len, c)

        # 2. Верхний правый угол
        painter.fillRect(r - corner_len + 1, t, corner_len, thickness, c)
        painter.fillRect(r - thickness + 1, t, thickness, corner_len, c)

        # 3. Нижний левый угол
        painter.fillRect(l, b - thickness + 1, corner_len, thickness, c)
        painter.fillRect(l, b - corner_len + 1, thickness, corner_len, c)

        # 4. Нижний правый угол
        painter.fillRect(r - corner_len + 1, b - thickness + 1, corner_len, thickness, c)
        painter.fillRect(r - thickness + 1, b - corner_len + 1, thickness, corner_len, c)

        # 5. Центральное перекрестие (+) белого цвета (#FFFFFF)
        cross_sz = snap_pixel(PIXEL_SIZE * 2)
        white_c = QColor(COLOR_WHITE)
        white_c.setAlpha(alpha)
        painter.fillRect(cx - cross_sz, cy - thickness // 2, cross_sz * 2, thickness, white_c)
        painter.fillRect(cx - thickness // 2, cy - cross_sz, thickness, cross_sz * 2, white_c)


class CyberShockwaveRing:
    """
    Расширяющаяся кибернетическая волна перегрузки со срезанными под 45° углами (Cyber Octagon).
    """

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

        for i in range(len(pts)):
            p1 = pts[i]
            p2 = pts[(i + 1) % len(pts)]
            painter.drawLine(p1, p2)
