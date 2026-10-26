from __future__ import annotations

import math
import random
from typing import Callable, List, Tuple

from PySide6.QtCore import QElapsedTimer, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

# --- Константы пиксельного стиля ---
PIXEL_SIZE = 4

# Цвета глитчей (Строго по ТЗ: красный, розовый, чёрный, зелёный)
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


def _snap(val: float | int, step: int = PIXEL_SIZE) -> int:
    """Привязка координаты к пиксельной сетке."""
    return int(val // step) * step


def _perimeter_points(rect: QRect, count: int) -> List[QPoint]:
    """Случайные точки на периметре прямоугольника с пиксельным квантованием."""
    result: List[QPoint] = []
    if rect.width() <= 0 or rect.height() <= 0:
        return result
    for _ in range(count):
        side = random.randrange(4)
        if side == 0:  # Верх
            x = _snap(random.randint(rect.left(), rect.right()))
            y = _snap(rect.top())
        elif side == 1:  # Право
            x = _snap(rect.right())
            y = _snap(random.randint(rect.top(), rect.bottom()))
        elif side == 2:  # Низ
            x = _snap(random.randint(rect.left(), rect.right()))
            y = _snap(rect.bottom())
        else:  # Лево
            x = _snap(rect.left())
            y = _snap(random.randint(rect.top(), rect.bottom()))
        result.append(QPoint(x, y))
    return result


def _edge_points(screen: QRect, count: int) -> List[QPoint]:
    """Случайные точки на краях экрана с пиксельным квантованием."""
    result: List[QPoint] = []
    for _ in range(count):
        side = random.randrange(4)
        if side == 0:
            x = _snap(random.randint(screen.left(), screen.right()))
            y = _snap(screen.top())
        elif side == 1:
            x = _snap(screen.right())
            y = _snap(random.randint(screen.top(), screen.bottom()))
        elif side == 2:
            x = _snap(random.randint(screen.left(), screen.right()))
            y = _snap(screen.bottom())
        else:
            x = _snap(screen.left())
            y = _snap(random.randint(screen.top(), screen.bottom()))
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
        sx = _snap(self.x)
        sy = _snap(self.y)
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
            px = _snap(bx + nx * jitter)
            py = _snap(by + ny * jitter)
            cur = QPoint(px, py)
            key_points.append(cur)

        key_points.append(QPoint(ex, ey))

        # Превращаем контрольные точки в пиксельные ступени (Manhattan staircase)
        for i in range(len(key_points) - 1):
            p1 = key_points[i]
            p2 = key_points[i + 1]
            # Ступенчатое соединение: сначала горизонталь, затем вертикаль (или наоборот)
            if random.random() < 0.5:
                mid = QPoint(_snap(p2.x()), _snap(p1.y()))
            else:
                mid = QPoint(_snap(p1.x()), _snap(p2.y()))
            self.segments.append((p1, mid))
            self.segments.append((mid, p2))

            # Генерация боковых ветвей (ветвление молнии)
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
        # Поворот вектора примерно на 45-60 градусов
        rad = math.atan2(main_dy, main_dx) + angle_sign * random.uniform(0.6, 1.1)
        branch_len = random.uniform(30.0, min(120.0, main_dist * 0.35))
        bx = origin.x() + math.cos(rad) * branch_len
        by = origin.y() + math.sin(rad) * branch_len

        cur = origin
        num_sub = max(2, int(branch_len // 22))
        for step in range(1, num_sub + 1):
            t = step / num_sub
            target_x = _snap(origin.x() + (bx - origin.x()) * t + random.randint(-12, 12))
            target_y = _snap(origin.y() + (by - origin.y()) * t + random.randint(-12, 12))
            nxt = QPoint(target_x, target_y)
            mid = QPoint(_snap(nxt.x()), _snap(cur.y()))
            branch.append((cur, mid))
            branch.append((mid, nxt))
            cur = nxt
        return branch

    def jitter(self) -> None:
        """Легкая вибрация молнии при каждом кадре."""
        if random.random() < 0.35:
            self._rebuild()

    def draw(self, painter: QPainter, progress: float) -> None:
        """Отрисовка пиксельной молнии: розовый ореол + неоновое бело-розовое ядро."""
        if not self.segments or progress <= 0:
            return

        visible_count = max(1, int(len(self.segments) * min(1.0, progress)))

        # 1. Слой ореола (Halo) - розовый пиксельный контур толщиной 2 блока (8px)
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

        # 2. Слой ядра (Core) - бело-розовая линия толщиной 1 пиксельный блок (4px)
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


class TransitionOverlay(QWidget):
    finished = Signal()

    def __init__(
        self,
        screen_rect: QRect,
        window_rect: QRect,
        mode: str,
        parent: QWidget | None = None,
        target: QWidget | None = None,
        on_peak: Callable[[], None] | None = None,
    ) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(None, flags)
        self._screen_rect = QRect(screen_rect)
        self._window_rect = QRect(window_rect)
        self._mode = mode  # "out" (пропадание) или "in" (появление)
        self._target = target
        self._on_peak = on_peak
        self._peak_called = False

        self._duration_ms = DURATION_OUT_MS if mode == "out" else DURATION_IN_MS
        self._progress = 0.0
        self._clock: QElapsedTimer | None = None
        self._last_elapsed = 0

        # Снимок целевого окна для красивого пиксельного распада/глитча
        self._target_pixmap: QPixmap | None = None
        if target is not None and target.isVisible() and target.width() > 0 and target.height() > 0:
            try:
                self._target_pixmap = target.grab()
            except Exception:
                self._target_pixmap = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(self._screen_rect)

        # Создаем пиксельные молнии
        self._bolts: List[PixelLightningBolt] = []
        bolt_count = 46
        if mode == "out":
            # При пропадании молнии вырываются из контура окна наружу к краям экрана
            starts = _perimeter_points(self._window_rect, bolt_count)
            ends = _edge_points(self._screen_rect, bolt_count)
        else:
            # При появлении молнии сходятся со всего экрана к окну
            starts = _edge_points(self._screen_rect, bolt_count)
            ends = _perimeter_points(self._window_rect, bolt_count)

        for s, e in zip(starts, ends):
            self._bolts.append(PixelLightningBolt(s, e))

        # Список пиксельных искр
        self._sparks: List[PixelSpark] = []

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._clock = QElapsedTimer()
        self._clock.start()
        self._last_elapsed = 0
        self.raise_()
        self.show()
        self._timer.start()

    def _tick(self) -> None:
        if self._clock is None:
            return
        elapsed = self._clock.elapsed()
        dt = max(0.001, (elapsed - self._last_elapsed) / 1000.0)
        self._last_elapsed = elapsed

        self._progress = min(1.0, elapsed / self._duration_ms)

        # Вызов коллбэка на пике анимации (когда происходит красная вспышка)
        peak_threshold = 0.52 if self._mode == "out" else 0.45
        if self._progress >= peak_threshold and not self._peak_called:
            self._peak_called = True
            if self._on_peak is not None:
                try:
                    self._on_peak()
                except Exception:
                    pass
            # Если целевой виджет скрывается при "out"
            if self._mode == "out" and self._target is not None and self._target.isVisible():
                self._target.hide()

        # Обновление и генерация искр
        wr = self._window_rect.translated(-self._screen_rect.topLeft())
        cx = wr.center().x()
        cy = wr.center().y()

        # Во время вспышки рождаются новые пиксельные искры красного и розового цвета
        flash_active = (0.42 <= self._progress <= 0.85) if self._mode == "out" else (0.28 <= self._progress <= 0.80)
        if flash_active:
            spark_color_pool = (
                QColor(255, 0, 50),
                QColor(255, 45, 125),
                QColor(255, 105, 180),
                QColor(255, 235, 245),
            )
            for _ in range(8):
                angle = random.uniform(0, math.tau)
                speed = random.uniform(80.0, 500.0)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                spark_x = cx + random.randint(-wr.width() // 3, wr.width() // 3)
                spark_y = cy + random.randint(-wr.height() // 3, wr.height() // 3)
                spark = PixelSpark(
                    spark_x,
                    spark_y,
                    vx,
                    vy,
                    random.choice(spark_color_pool),
                    random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)),
                    random.uniform(0.18, 0.45),
                )
                self._sparks.append(spark)

        # Шаг физики искр
        self._sparks = [s for s in self._sparks if s.step(dt)]

        # Дрожание молний
        for bolt in self._bolts:
            bolt.jitter()

        self.update()

        if self._progress >= 1.0:
            self._timer.stop()
            self.finished.emit()
            self.close()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        # Отключаем антиалиасинг для сохранения истинного пиксельного стиля
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        p = self._progress
        wr = self._window_rect.translated(-self._screen_rect.topLeft())

        if self._mode == "out":
            self._paint_out(painter, p, wr)
        else:
            self._paint_in(painter, p, wr)

        painter.end()

    # =========================================================================
    # РЕЖИМ ПРОПАДАНИЯ ("OUT")
    # 1. Всё окно/облик покрывается сильными пиксельными глитчами
    #    (красный, розовый, чёрный, зелёный).
    # 2. Красная вспышка с розовыми молниями в пиксельном стиле.
    # =========================================================================
    def _paint_out(self, painter: QPainter, p: float, wr: QRect) -> None:
        # Фаза 1: Сильные пиксельные глитчи (0.0 -> 0.55)
        if p < 0.55:
            intensity = min(1.0, (p / 0.45) ** 1.3)
            self._paint_pixel_glitches_on_window(painter, wr, intensity)

        # Фаза 2: Красная вспышка (0.42 -> 0.92)
        if 0.42 <= p <= 0.92:
            flash_p = (p - 0.42) / 0.50
            self._paint_red_pixel_flash(painter, wr, flash_p)

        # Фаза 3: Розовые молнии (0.40 -> 0.95)
        if p >= 0.40:
            bolt_t = min(1.0, (p - 0.40) / 0.45)
            # Притухание к концу
            if p > 0.85:
                fade_alpha = max(0, int(255 * (1.0 - (p - 0.85) / 0.15)))
                painter.setOpacity(fade_alpha / 255.0)
            for bolt in self._bolts:
                bolt.draw(painter, bolt_t)
            painter.setOpacity(1.0)

        # Отрисовка пиксельных искр
        for spark in self._sparks:
            spark.draw(painter)

    # =========================================================================
    # РЕЖИМ ПОЯВЛЕНИЯ ("IN")
    # Красная вспышка с молниями в пиксельном стиле,
    # переходящая в материализацию окна/облика.
    # =========================================================================
    def _paint_in(self, painter: QPainter, p: float, wr: QRect) -> None:
        # Фаза 1: Молнии устремляются со всего экрана в точку появления (0.0 -> 0.65)
        if p < 0.65:
            bolt_t = min(1.0, p / 0.40)
            for bolt in self._bolts:
                bolt.draw(painter, bolt_t)

        # Фаза 2: Красная пиксельная вспышка (0.28 -> 0.82)
        if 0.28 <= p <= 0.82:
            flash_p = (p - 0.28) / 0.54
            self._paint_red_pixel_flash(painter, wr, flash_p)

        # Фаза 3: Остаточный пиксельный контур и стабилизация (0.60 -> 1.0)
        if p >= 0.60:
            stabilize_p = (p - 0.60) / 0.40
            rem_glitch = max(0.0, 1.0 - stabilize_p)
            if rem_glitch > 0.05:
                # Легкие остаточные пиксельные глитчи при материализации
                self._paint_pixel_glitches_on_window(painter, wr, rem_glitch * 0.4)

            # Пиксельная неоновая рамка окна на выходе
            border_alpha = int(220 * (1.0 - stabilize_p))
            if border_alpha > 0:
                pen = QPen(QColor(255, 45, 125, border_alpha), PIXEL_SIZE)
                painter.setPen(pen)
                painter.drawRect(wr)

        # Отрисовка пиксельных искр
        for spark in self._sparks:
            spark.draw(painter)

    # =========================================================================
    # ГЕНЕРАЦИЯ СИЛЬНЫХ ПИКСЕЛЬНЫХ ГЛИТЧЕЙ
    # Цвета строго: Красный, Розовый, Чёрный, Зелёный
    # =========================================================================
    def _paint_pixel_glitches_on_window(
        self, painter: QPainter, wr: QRect, intensity: float
    ) -> None:
        """Покрывает окно/облик плотным массивом пиксельных глитчей 4 цветов."""
        if wr.width() <= 0 or wr.height() <= 0:
            return

        w = wr.width()
        h = wr.height()
        left = wr.left()
        top = wr.top()

        # 1. Если есть снимок окна, рисуем его с пиксельными разрывами (tearing/slices)
        if self._target_pixmap is not None and not self._target_pixmap.isNull():
            slice_count = int(8 + 32 * intensity)
            for _ in range(slice_count):
                sy = random.randint(0, max(0, h - PIXEL_SIZE * 2))
                sh = _snap(random.randint(PIXEL_SIZE, PIXEL_SIZE * 4))
                sh = min(sh, h - sy)
                if sh <= 0:
                    continue
                # Пиксельный сдвиг полосы по горизонтали
                shift_max = int((w // 6) * intensity)
                dx = _snap(random.randint(-shift_max, shift_max))

                src_rect = QRect(0, sy, w, sh)
                dst_rect = QRect(left + dx, top + sy, w, sh)
                painter.drawPixmap(dst_rect, self._target_pixmap, src_rect)

        # 2. Полноширинные горизонтальные глитч-полосы 4 цветов (Красный, Розовый, Черный, Зеленый)
        bar_count = int(6 + 24 * intensity)
        for _ in range(bar_count):
            y = top + _snap(random.randint(0, max(0, h - PIXEL_SIZE)))
            bar_h = _snap(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 3)))
            color = QColor(random.choice(ALL_GLITCH_COLORS))
            color.setAlpha(random.randint(140, 240))
            painter.fillRect(left, y, w, bar_h, color)

        # 3. Пиксельные блоки/тайлы повреждения (Corruption Blocks)
        # Размеры кратны PIXEL_SIZE: 4x4, 8x8, 16x8, 24x12, 32x16
        block_count = int(25 + 160 * intensity)
        for _ in range(block_count):
            bx = left + _snap(random.randint(0, max(0, w - PIXEL_SIZE)))
            by = top + _snap(random.randint(0, max(0, h - PIXEL_SIZE)))
            bw = _snap(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 4, PIXEL_SIZE * 6)))
            bh = _snap(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 3)))
            bw = min(bw, wr.right() - bx + 1)
            bh = min(bh, wr.bottom() - by + 1)
            if bw <= 0 or bh <= 0:
                continue
            color = QColor(random.choice(ALL_GLITCH_COLORS))
            color.setAlpha(random.randint(160, 255))
            painter.fillRect(bx, by, bw, bh, color)

        # 4. Пиксельный матричный шум (зерно 4 цветов)
        noise_count = int(60 + 350 * intensity)
        for _ in range(noise_count):
            nx = left + _snap(random.randint(0, max(0, w - PIXEL_SIZE)))
            ny = top + _snap(random.randint(0, max(0, h - PIXEL_SIZE)))
            color = QColor(random.choice(ALL_GLITCH_COLORS))
            color.setAlpha(random.randint(180, 255))
            painter.fillRect(nx, ny, PIXEL_SIZE, PIXEL_SIZE, color)

        # 5. При сильном глитче (intensity > 0.6) - черные полосы блэкаута и инверсии
        if intensity > 0.6:
            blackout_count = int(4 + 10 * intensity)
            for _ in range(blackout_count):
                by = top + _snap(random.randint(0, max(0, h - PIXEL_SIZE * 2)))
                bh = _snap(random.randint(PIXEL_SIZE * 2, PIXEL_SIZE * 6))
                painter.fillRect(left, by, w, bh, QColor(0, 0, 0, 230))

    # =========================================================================
    # РЕНДЕРИНГ КРАСНОЙ ПИКСЕЛЬНОЙ ВСПЫШКИ (Red Pixel Flash)
    # С пиксельным дизерингом и расширяющимися волнами
    # =========================================================================
    def _paint_red_pixel_flash(self, painter: QPainter, wr: QRect, flash_p: float) -> None:
        """Ослепительная красная вспышка в пиксельном стиле."""
        # Кривая вспышки: резкий пик в начале, плавный экспоненциальный спад
        if flash_p <= 0.25:
            flash_intensity = flash_p / 0.25
        else:
            flash_intensity = max(0.0, 1.0 - (flash_p - 0.25) / 0.75) ** 1.8

        if flash_intensity <= 0.01:
            return

        cx = wr.center().x()
        cy = wr.center().y()
        max_dim = max(wr.width(), wr.height())

        # 1. Полноэкранный полупрозрачный красный фон вспышки
        screen_alpha = int(90 * flash_intensity)
        if screen_alpha > 0:
            painter.fillRect(self.rect(), QColor(255, 0, 30, screen_alpha))

        # 2. Ослепительно яркое ядро вспышки поверх окна
        # Пиксельная заливка области окна красным светом
        core_alpha = int(240 * flash_intensity)
        painter.fillRect(wr, QColor(255, 10, 50, core_alpha))

        # Бело-розовый центр вспышки в сердцевине
        if flash_intensity > 0.4:
            hot_w = _snap(wr.width() * 0.6)
            hot_h = _snap(wr.height() * 0.6)
            hot_rect = QRect(cx - hot_w // 2, cy - hot_h // 2, hot_w, hot_h)
            hot_alpha = int(200 * ((flash_intensity - 0.4) / 0.6))
            painter.fillRect(hot_rect, QColor(255, 230, 245, hot_alpha))

        # 3. Расширяющиеся пиксельные ударные волны красного цвета (концентрические ступени)
        expand_dist = _snap(max_dim * 1.5 * flash_p)
        wave_rect = wr.adjusted(-expand_dist, -expand_dist, expand_dist, expand_dist)
        wave_alpha = int(220 * flash_intensity)
        if wave_alpha > 0 and wave_rect.width() > 0:
            pen = QPen(QColor(255, 0, 40, wave_alpha), PIXEL_SIZE * 2)
            painter.setPen(pen)
            painter.drawRect(wave_rect)

            # Вторая волна со смещением
            if expand_dist > PIXEL_SIZE * 8:
                inner_dist = expand_dist - PIXEL_SIZE * 6
                inner_rect = wr.adjusted(-inner_dist, -inner_dist, inner_dist, inner_dist)
                pen2 = QPen(QColor(255, 45, 120, int(wave_alpha * 0.7)), PIXEL_SIZE)
                painter.setPen(pen2)
                painter.drawRect(inner_rect)

        # 4. Пиксельный дизеринг (Bayer Matrix) ореола вспышки
        dither_zone = wr.adjusted(
            -PIXEL_SIZE * 18, -PIXEL_SIZE * 18, PIXEL_SIZE * 18, PIXEL_SIZE * 18
        )
        dither_step = PIXEL_SIZE * 2
        dither_color = QColor(255, 0, 45, int(180 * flash_intensity))

        # Отрисовка пиксельного дизеринга по границам вспышки
        for y in range(dither_zone.top(), dither_zone.bottom(), dither_step):
            for x in range(dither_zone.left(), dither_zone.right(), dither_step):
                # Пропускаем центр, где заливка сплошная
                if wr.contains(x, y):
                    continue
                bx = (x // dither_step) % 4
                by = (y // dither_step) % 4
                threshold = BAYER_4X4[by][bx] / 16.0
                if flash_intensity > threshold:
                    painter.fillRect(x, y, dither_step, dither_step, dither_color)
