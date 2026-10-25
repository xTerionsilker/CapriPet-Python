from __future__ import annotations

import math
import random
from typing import List, Tuple

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


_BOLT_COLOR = (255, 45, 115)
_DURATION_MS = 300


def _perimeter_points(rect: QRect, count: int) -> List[QPoint]:
    result: List[QPoint] = []
    if rect.width() <= 0 or rect.height() <= 0:
        return result
    for _ in range(count):
        side = random.randrange(4)
        if side == 0:
            x = random.randint(rect.left(), rect.right())
            y = rect.top()
        elif side == 1:
            x = rect.right()
            y = random.randint(rect.top(), rect.bottom())
        elif side == 2:
            x = random.randint(rect.left(), rect.right())
            y = rect.bottom()
        else:
            x = rect.left()
            y = random.randint(rect.top(), rect.bottom())
        result.append(QPoint(x, y))
    return result


def _edge_points(screen: QRect, count: int) -> List[QPoint]:
    result: List[QPoint] = []
    for _ in range(count):
        side = random.randrange(4)
        if side == 0:
            x = random.randint(screen.left(), screen.right())
            y = screen.top()
        elif side == 1:
            x = screen.right()
            y = random.randint(screen.top(), screen.bottom())
        elif side == 2:
            x = random.randint(screen.left(), screen.right())
            y = screen.bottom()
        else:
            x = screen.left()
            y = random.randint(screen.top(), screen.bottom())
        result.append(QPoint(x, y))
    return result


def _jagged_path(start: QPoint, end: QPoint, segments: int = 18) -> List[QPoint]:
    points = [start]
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    for i in range(1, segments):
        t = i / segments
        base_x = start.x() + dx * t
        base_y = start.y() + dy * t
        # perpendicular jitter
        nx = -dy
        ny = dx
        length = math.hypot(nx, ny) or 1.0
        jitter = random.uniform(-0.45, 0.45) * max(60.0, math.hypot(dx, dy) * 0.22)
        px = base_x + nx / length * jitter
        py = base_y + ny / length * jitter
        points.append(QPoint(int(px), int(py)))
    points.append(end)
    return points


def _partial_polyline(points: List[QPoint], t: float) -> List[QPoint]:
    if not points or t <= 0:
        return []
    if t >= 1:
        return list(points)
    # cumulative distances
    dists = [0.0]
    for i in range(1, len(points)):
        prev = points[i - 1]
        cur = points[i]
        dists.append(dists[-1] + math.hypot(cur.x() - prev.x(), cur.y() - prev.y()))
    total = dists[-1]
    if total <= 0:
        return [points[0]]
    target = total * t
    result = [points[0]]
    for i in range(1, len(points)):
        if dists[i] <= target:
            result.append(points[i])
            continue
        prev = points[i - 1]
        cur = points[i]
        seg_len = dists[i] - dists[i - 1]
        if seg_len <= 0:
            break
        frac = (target - dists[i - 1]) / seg_len
        x = int(prev.x() + (cur.x() - prev.x()) * frac)
        y = int(prev.y() + (cur.y() - prev.y()) * frac)
        result.append(QPoint(x, y))
        break
    return result


class TransitionOverlay(QWidget):
    finished = Signal()

    def __init__(
        self,
        screen_rect: QRect,
        window_rect: QRect,
        mode: str,
        parent: QWidget | None = None,
    ) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(None, flags)
        self._screen_rect = QRect(screen_rect)
        self._window_rect = QRect(window_rect)
        self._mode = mode  # "out" or "in"
        self._progress = 0.0
        self._start_ms = 0
        self._clock = None
        self._bolts: List[List[QPoint]] = []
        self._bolt_colors: List[QColor] = []
        self._bolt_widths: List[int] = []
        self._glitch_phase = mode == "out"

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(self._screen_rect)

        bolt_count = 52
        if mode == "out":
            starts = _perimeter_points(self._window_rect, bolt_count)
            ends = _edge_points(self._screen_rect, bolt_count)
        else:
            starts = _edge_points(self._screen_rect, bolt_count)
            ends = _perimeter_points(self._window_rect, bolt_count)
        for s, e in zip(starts, ends):
            segs = random.randint(14, 26)
            self._bolts.append(_jagged_path(s, e, segments=segs))
            self._bolt_colors.append(QColor(*_BOLT_COLOR))
            self._bolt_widths.append(random.choice((1, 1, 2, 2, 3, 4)))

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        from PySide6.QtCore import QElapsedTimer

        self._clock = QElapsedTimer()
        self._clock.start()
        self.show()
        self._timer.start()

    def _tick(self) -> None:
        if self._clock is None:
            return
        elapsed = self._clock.elapsed()
        self._progress = min(1.0, elapsed / _DURATION_MS)
        self.update()
        if self._progress >= 1.0:
            self._timer.stop()
            self.finished.emit()
            self.close()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        p = self._progress
        if self._mode == "out":
            # glitch/crash on window area during first part
            if p < 0.25:
                local_p = p / 0.25
                wr = self._window_rect.translated(-self._screen_rect.topLeft())
                # draw window as glitchy rect
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                for _ in range(int(6 + 20 * (1 - local_p))):
                    x = wr.left() + random.randint(0, max(1, wr.width() - 1))
                    y = wr.top() + random.randint(0, max(1, wr.height() - 1))
                    w = random.randint(4, max(5, wr.width() // 6))
                    h = random.randint(1, 4)
                    c = QColor(*_BOLT_COLOR, random.randint(40, 120))
                    painter.fillRect(x, y, min(w, wr.right() - x + 1), h, c)
                # tears
                for _ in range(int(4 + 12 * (1 - local_p))):
                    y = wr.top() + random.randint(0, max(1, wr.height() - 1))
                    band = random.randint(1, 3)
                    c = QColor(*_BOLT_COLOR)
                    c.setAlpha(random.randint(30, 90))
                    painter.fillRect(wr.left(), y, wr.width(), band, c)
            # radiating bolts: grow outward as p increases
            bolt_t = max(0.0, (p - 0.05) / 0.95) if p > 0.05 else 0.0
            for bolt, color, width in zip(self._bolts, self._bolt_colors, self._bolt_widths):
                poly = _partial_polyline(bolt, bolt_t)
                if len(poly) < 2:
                    continue
                # glow
                glow = QColor(color)
                glow.setAlpha(230)
                pen = QPen(glow, max(1, width + 2))
                painter.setPen(pen)
                for i in range(1, len(poly)):
                    painter.drawLine(poly[i - 1], poly[i])
                # core
                core = QColor(255, 230, 245, 240)
                pen2 = QPen(core, max(1, width))
                painter.setPen(pen2)
                for i in range(1, len(poly)):
                    painter.drawLine(poly[i - 1], poly[i])
        else:
            # gathering bolts: grow inward as p increases
            bolt_t = p
            for bolt, color, width in zip(self._bolts, self._bolt_colors, self._bolt_widths):
                poly = _partial_polyline(bolt, bolt_t)
                if len(poly) < 2:
                    continue
                glow = QColor(color)
                glow.setAlpha(230)
                pen = QPen(glow, max(1, width + 2))
                painter.setPen(pen)
                for i in range(1, len(poly)):
                    painter.drawLine(poly[i - 1], poly[i])
                core = QColor(255, 230, 245, 240)
                pen2 = QPen(core, max(1, width))
                painter.setPen(pen2)
                for i in range(1, len(poly)):
                    painter.drawLine(poly[i - 1], poly[i])
            # target window outline flash near end
            if p > 0.75:
                alpha = int(200 * ((p - 0.75) / 0.25))
                wr = self._window_rect.translated(-self._screen_rect.topLeft())
                pen = QPen(QColor(255, 90, 160, alpha), 2)
                painter.setPen(pen)
                painter.drawRect(wr)

        painter.end()