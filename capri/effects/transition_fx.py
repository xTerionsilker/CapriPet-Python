from __future__ import annotations

import math
import random
from typing import List, Tuple

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygon

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


# Длительность переходов (мс) — чуть длиннее, чтобы раскрыть хакерскую последовательность
DURATION_OUT_MS = 780
DURATION_IN_MS = 720
DURATION_POINT_MS = 680

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
        color_scheme: str = "crimson",  # "crimson", "green", "blue" или "violet"
        branch_chance: float = 0.30,
    ) -> None:
        self.start = snap_point(start)
        self.end = snap_point(end)
        self.color_scheme = color_scheme
        self._branch_chance = max(0.0, min(1.0, branch_chance))
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

            if random.random() < self._branch_chance and i < len(key_points) - 2:
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

        # Цвета в зависимости от схемы (редкие синие/фиолетовые каналы — по палитре Капри)
        if self.color_scheme == "green":
            primary_color = COLOR_ACID_GREEN
            aberration_color = COLOR_CRIMSON
            sub_packet_color = COLOR_CRIMSON
        elif self.color_scheme == "blue":
            primary_color = COLOR_ELECTRIC_BLUE
            aberration_color = COLOR_VIOLET
            sub_packet_color = COLOR_ACID_GREEN
        elif self.color_scheme == "violet":
            primary_color = COLOR_VIOLET
            aberration_color = COLOR_ELECTRIC_BLUE
            sub_packet_color = COLOR_CRIMSON
        else:
            primary_color = COLOR_CRIMSON
            aberration_color = COLOR_ACID_GREEN
            sub_packet_color = COLOR_ACID_GREEN

        # Слой 1: Темная обсидиановая подложка (#0B0B0B, толщина 8px) для резкого кибер-контраста
        obsidian_pen = QPen(QColor(COLOR_OBSIDIAN.red(), COLOR_OBSIDIAN.green(), COLOR_OBSIDIAN.blue(), 170), PIXEL_SIZE * 2)
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
        neon_glow.setAlpha(215)
        glow_pen = QPen(neon_glow, PIXEL_SIZE + 1)
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

        # Слой 4: Белое ядро (#FFFFFF 2%, тонкое, чтобы не пересвечивать кадр)
        core_pen = QPen(with_alpha(COLOR_WHITE, 150), 2)
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


# ---------------------------------------------------------------------------
# Cyberpunk 2077 / Kiroshi / quickhack primitives
# ---------------------------------------------------------------------------


def with_alpha(color: QColor, alpha: int) -> QColor:
    """Возвращает копию цвета с ограниченной альфой."""
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c


def chamfer_points(rect: QRect, cut: int) -> QPolygon:
    """Полигон с срезанными под 45° углами — фирменная форма панелей Night City."""
    cut = max(2, min(cut, min(rect.width(), rect.height()) // 3))
    l, r, t, b = rect.left(), rect.right(), rect.top(), rect.bottom()
    return QPolygon(
        [
            QPoint(l + cut, t),
            QPoint(r - cut, t),
            QPoint(r, t + cut),
            QPoint(r, b - cut),
            QPoint(r - cut, b),
            QPoint(l + cut, b),
            QPoint(l, b - cut),
            QPoint(l, t + cut),
        ]
    )


def draw_scanlines(
    painter: QPainter,
    rect: QRect,
    alpha: int = 34,
    spacing: int = 4,
) -> None:
    """Тонкие ЭЛТ-сканлайны поверх экрана."""
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
    """Бегущая полоса оптического сканирования Kiroshi."""
    if rect.height() <= 0:
        return
    y = rect.top() + int(rect.height() * (progress % 1.0))
    for offset, alpha, height in ((-6, 28, 1), (-2, 70, 1), (0, 210, 2), (3, 90, 1)):
        painter.fillRect(
            rect.left(),
            max(rect.top(), min(rect.bottom(), y + offset)),
            rect.width(),
            height,
            with_alpha(color, alpha),
        )
    # Пиксельные обрывки по краям луча
    rng = random.Random(int(progress * 1000) + rect.width())
    for _ in range(7):
        bx = rng.randint(rect.left(), max(rect.left(), rect.right() - 40))
        bw = rng.choice((8, 16, 32, 64))
        painter.fillRect(
            bx,
            y + rng.choice((-4, 0, 4)),
            min(bw, rect.right() - bx),
            2,
            with_alpha(rng.choice((COLOR_CRIMSON, COLOR_ACID_GREEN, COLOR_WHITE)), 150),
        )


def draw_screen_glitch_bars(
    painter: QPainter,
    rect: QRect,
    progress: float,
    intensity: float = 1.0,
) -> None:
    """Горизонтальные сбои кадра (datamosh / tracking error) по всей ширине экрана."""
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
            (COLOR_CRIMSON, COLOR_OBSIDIAN, COLOR_ACID_GREEN, COLOR_ELECTRIC_BLUE),
            weights=(52, 30, 14, 4),
            k=1,
        )[0]
        painter.fillRect(x, y, w, h, with_alpha(color, int(rng.randint(50, 150) * intensity)))


def draw_hazard_frame(
    painter: QPainter,
    rect: QRect,
    intensity: float = 1.0,
    color: QColor = COLOR_CRIMSON,
) -> None:
    """Аварийная рамка с диагональными полосами (красно-чёрная, вместо жёлтой CP2077)."""
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


class CyberKiroshiReticle:
    """Оптический прицел Kiroshi: вращающиеся деления, скобки и телеметрия цели."""

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
            COLOR_ACID_GREEN if color != COLOR_ACID_GREEN else COLOR_CRIMSON,
            int(alpha * 0.8),
        )

        # Угловые скобки и перекрестие — базовая оптика
        CyberHoloReticle.draw(
            painter, rect, progress, color=color, bracket_offset=bracket_offset
        )

        cx = rect.center().x()
        cy = rect.center().y()
        radius = max(18, min(rect.width(), rect.height()) // 2 + bracket_offset)
        radius = snap_pixel(radius)

        # Вращающееся кольцо тиков
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

        # Сегментированные дуги захвата
        arc_rect = QRectF(cx - radius - 16, cy - radius - 16, (radius + 16) * 2, (radius + 16) * 2)
        pen = QPen(with_alpha(color, int(alpha * 0.75)), 2)
        painter.setPen(pen)
        for start in (15, 105, 195, 285):
            painter.drawArc(arc_rect, int((start + math.degrees(rotation)) * 16), int(38 * 16))

        # Обсидиановый контур под меткой цели
        if label:
            font = QFont("Monospace")
            font.setStyleHint(QFont.StyleHint.Monospace)
            font.setPixelSize(10)
            font.setBold(True)
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

        # Маркер захвата в центре
        if locked:
            size = snap_pixel(max(6, radius // 8))
            painter.fillRect(cx - size // 2, cy - size // 2, size, size, with_alpha(COLOR_WHITE, alpha))
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
    """Панель загрузки быстрого взлома: сегментированный прогресс и телеметрия."""
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

    font = QFont("Monospace")
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(9)
    font.setBold(True)
    painter.setFont(font)

    label_y = rect.top() + 12
    painter.setPen(with_alpha(COLOR_WHITE, 235))
    painter.drawText(rect.left() + 9, label_y, f"{title} // {status}")
    percent_text = f"{int(progress * 100):03d}%"
    painter.setPen(with_alpha(color, 255))
    painter.drawText(
        rect.right() - 9 - painter.fontMetrics().horizontalAdvance(percent_text),
        label_y,
        percent_text,
    )

    # Сегментированная полоса RAM / прогресса
    bar = QRect(rect.left() + 9, rect.bottom() - 10, rect.width() - 18, 5)
    segments = max(8, bar.width() // 6)
    gap = 2
    seg_w = max(1, (bar.width() - gap * (segments - 1)) // segments)
    filled = int(segments * progress)
    for i in range(segments):
        x = bar.left() + i * (seg_w + gap)
        if i < filled:
            seg_color = color if i % 5 else COLOR_ACID_GREEN
            painter.fillRect(x, bar.top(), seg_w, bar.height(), with_alpha(seg_color, 240))
        else:
            painter.fillRect(x, bar.top(), seg_w, bar.height(), with_alpha(COLOR_CRIMSON, 40))
    painter.restore()


def draw_breach_grid(
    painter: QPainter,
    rect: QRect,
    progress: float,
    seed: int = 0,
    cell: int = 10,
    color: QColor = COLOR_ACID_GREEN,
) -> None:
    """Матрица Breach Protocol вокруг курсора/цели."""
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
                c = color if r > 0.18 else rng.choice((COLOR_CRIMSON, COLOR_ELECTRIC_BLUE, COLOR_VIOLET))
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

    # Активная линия взлома
    line_y = rect.top() + int(rect.height() * progress)
    painter.fillRect(rect.left(), line_y, rect.width(), 2, with_alpha(color, 210))
    painter.fillRect(rect.left(), line_y - 2, rect.width(), 1, with_alpha(COLOR_WHITE, 120))
    painter.restore()


def draw_hex_stream(
    painter: QPainter,
    rect: QRect,
    progress: float,
    columns: int = 14,
    color: QColor = COLOR_ACID_GREEN,
) -> None:
    """Столбцы глифов, стекающие по экрану, как в терминалах Night City."""
    if rect.width() <= 0 or rect.height() <= 0:
        return
    painter.save()
    painter.setClipRect(rect)
    font = QFont("Monospace")
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(9)
    font.setBold(True)
    painter.setFont(font)
    glyphs = "01ABCDEF<>/\\#%&"
    rng = random.Random(2077 + rect.width())
    for col in range(max(1, columns)):
        x = rect.left() + int((col + 0.5) * rect.width() / max(1, columns))
        speed = rng.uniform(0.55, 1.45)
        phase = rng.uniform(0.0, 1.0)
        head_y = rect.top() + int(((progress * speed + phase) % 1.0) * (rect.height() + 60)) - 30
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
    """Текст с хроматическим расслоением, как сбоящий HUD Relic."""
    font = QFont("Monospace")
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(size)
    font.setBold(True)
    painter.save()
    painter.setFont(font)
    painter.setPen(with_alpha(COLOR_CRIMSON, 170))
    painter.drawText(x - 1, y, text)
    painter.setPen(with_alpha(COLOR_ACID_GREEN, 150))
    painter.drawText(x + 1, y, text)
    painter.setPen(with_alpha(color, 245))
    painter.drawText(x, y, text)
    painter.restore()
