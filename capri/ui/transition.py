from __future__ import annotations

import random
from typing import Callable, List

from PySide6.QtCore import QElapsedTimer, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from .transition_fx import (
    ALL_GLITCH_COLORS,
    BAYER_4X4,
    DURATION_IN_MS,
    DURATION_OUT_MS,
    PIXEL_SIZE,
    PixelLightningBolt,
    PixelSpark,
    edge_points,
    perimeter_points,
    snap_pixel,
)


class TransitionOverlay(QWidget):
    """Полноэкранный оверлей пиксельных переходов появления и исчезновения питомца."""

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

        # Снимок целевого окна для пиксельного распада/глитча
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
            starts = perimeter_points(self._window_rect, bolt_count)
            ends = edge_points(self._screen_rect, bolt_count)
        else:
            starts = edge_points(self._screen_rect, bolt_count)
            ends = perimeter_points(self._window_rect, bolt_count)

        for s, e in zip(starts, ends):
            self._bolts.append(PixelLightningBolt(s, e))

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

        # Вызов коллбэка на пике анимации
        peak_threshold = 0.52 if self._mode == "out" else 0.45
        if self._progress >= peak_threshold and not self._peak_called:
            self._peak_called = True
            if self._on_peak is not None:
                try:
                    self._on_peak()
                except Exception:
                    pass
            if self._mode == "out" and self._target is not None and self._target.isVisible():
                self._target.hide()

        # Обновление и генерация искр
        wr = self._window_rect.translated(-self._screen_rect.topLeft())
        cx = wr.center().x()
        cy = wr.center().y()

        flash_active = (0.42 <= self._progress <= 0.85) if self._mode == "out" else (0.28 <= self._progress <= 0.80)
        if flash_active:
            import math
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

        self._sparks = [s for s in self._sparks if s.step(dt)]

        for bolt in self._bolts:
            bolt.jitter()

        self.update()

        if self._progress >= 1.0:
            self._timer.stop()
            self.finished.emit()
            self.close()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        p = self._progress
        wr = self._window_rect.translated(-self._screen_rect.topLeft())

        if self._mode == "out":
            self._paint_out(painter, p, wr)
        else:
            self._paint_in(painter, p, wr)

        painter.end()

    def _paint_out(self, painter: QPainter, p: float, wr: QRect) -> None:
        if p < 0.55:
            intensity = min(1.0, (p / 0.45) ** 1.3)
            self._paint_pixel_glitches_on_window(painter, wr, intensity)

        if 0.42 <= p <= 0.92:
            flash_p = (p - 0.42) / 0.50
            self._paint_red_pixel_flash(painter, wr, flash_p)

        if p >= 0.40:
            bolt_t = min(1.0, (p - 0.40) / 0.45)
            if p > 0.85:
                fade_alpha = max(0, int(255 * (1.0 - (p - 0.85) / 0.15)))
                painter.setOpacity(fade_alpha / 255.0)
            for bolt in self._bolts:
                bolt.draw(painter, bolt_t)
            painter.setOpacity(1.0)

        for spark in self._sparks:
            spark.draw(painter)

    def _paint_in(self, painter: QPainter, p: float, wr: QRect) -> None:
        if p < 0.65:
            bolt_t = min(1.0, p / 0.40)
            for bolt in self._bolts:
                bolt.draw(painter, bolt_t)

        if 0.28 <= p <= 0.82:
            flash_p = (p - 0.28) / 0.54
            self._paint_red_pixel_flash(painter, wr, flash_p)

        if p >= 0.60:
            stabilize_p = (p - 0.60) / 0.40
            rem_glitch = max(0.0, 1.0 - stabilize_p)
            if rem_glitch > 0.05:
                self._paint_pixel_glitches_on_window(painter, wr, rem_glitch * 0.4)

            border_alpha = int(220 * (1.0 - stabilize_p))
            if border_alpha > 0:
                pen = QPen(QColor(255, 45, 125, border_alpha), PIXEL_SIZE)
                painter.setPen(pen)
                painter.drawRect(wr)

        for spark in self._sparks:
            spark.draw(painter)

    def _paint_pixel_glitches_on_window(
        self, painter: QPainter, wr: QRect, intensity: float
    ) -> None:
        if wr.width() <= 0 or wr.height() <= 0:
            return

        w = wr.width()
        h = wr.height()
        left = wr.left()
        top = wr.top()

        if self._target_pixmap is not None and not self._target_pixmap.isNull():
            slice_count = int(8 + 32 * intensity)
            for _ in range(slice_count):
                sy = random.randint(0, max(0, h - PIXEL_SIZE * 2))
                sh = snap_pixel(random.randint(PIXEL_SIZE, PIXEL_SIZE * 4))
                sh = min(sh, h - sy)
                if sh <= 0:
                    continue
                shift_max = int((w // 6) * intensity)
                dx = snap_pixel(random.randint(-shift_max, shift_max))

                src_rect = QRect(0, sy, w, sh)
                dst_rect = QRect(left + dx, top + sy, w, sh)
                painter.drawPixmap(dst_rect, self._target_pixmap, src_rect)

        bar_count = int(6 + 24 * intensity)
        for _ in range(bar_count):
            y = top + snap_pixel(random.randint(0, max(0, h - PIXEL_SIZE)))
            bar_h = snap_pixel(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 3)))
            color = QColor(random.choice(ALL_GLITCH_COLORS))
            color.setAlpha(random.randint(140, 240))
            painter.fillRect(left, y, w, bar_h, color)

        block_count = int(25 + 160 * intensity)
        for _ in range(block_count):
            bx = left + snap_pixel(random.randint(0, max(0, w - PIXEL_SIZE)))
            by = top + snap_pixel(random.randint(0, max(0, h - PIXEL_SIZE)))
            bw = snap_pixel(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 4, PIXEL_SIZE * 6)))
            bh = snap_pixel(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 3)))
            bw = min(bw, wr.right() - bx + 1)
            bh = min(bh, wr.bottom() - by + 1)
            if bw <= 0 or bh <= 0:
                continue
            color = QColor(random.choice(ALL_GLITCH_COLORS))
            color.setAlpha(random.randint(160, 255))
            painter.fillRect(bx, by, bw, bh, color)

        noise_count = int(60 + 350 * intensity)
        for _ in range(noise_count):
            nx = left + snap_pixel(random.randint(0, max(0, w - PIXEL_SIZE)))
            ny = top + snap_pixel(random.randint(0, max(0, h - PIXEL_SIZE)))
            color = QColor(random.choice(ALL_GLITCH_COLORS))
            color.setAlpha(random.randint(180, 255))
            painter.fillRect(nx, ny, PIXEL_SIZE, PIXEL_SIZE, color)

        if intensity > 0.6:
            blackout_count = int(4 + 10 * intensity)
            for _ in range(blackout_count):
                by = top + snap_pixel(random.randint(0, max(0, h - PIXEL_SIZE * 2)))
                bh = snap_pixel(random.randint(PIXEL_SIZE * 2, PIXEL_SIZE * 6))
                painter.fillRect(left, by, w, bh, QColor(0, 0, 0, 230))

    def _paint_red_pixel_flash(self, painter: QPainter, wr: QRect, flash_p: float) -> None:
        if flash_p <= 0.25:
            flash_intensity = flash_p / 0.25
        else:
            flash_intensity = max(0.0, 1.0 - (flash_p - 0.25) / 0.75) ** 1.8

        if flash_intensity <= 0.01:
            return

        cx = wr.center().x()
        cy = wr.center().y()
        max_dim = max(wr.width(), wr.height())

        screen_alpha = int(90 * flash_intensity)
        if screen_alpha > 0:
            painter.fillRect(self.rect(), QColor(255, 0, 30, screen_alpha))

        core_alpha = int(240 * flash_intensity)
        painter.fillRect(wr, QColor(255, 10, 50, core_alpha))

        if flash_intensity > 0.4:
            hot_w = snap_pixel(wr.width() * 0.6)
            hot_h = snap_pixel(wr.height() * 0.6)
            hot_rect = QRect(cx - hot_w // 2, cy - hot_h // 2, hot_w, hot_h)
            hot_alpha = int(200 * ((flash_intensity - 0.4) / 0.6))
            painter.fillRect(hot_rect, QColor(255, 230, 245, hot_alpha))

        expand_dist = snap_pixel(max_dim * 1.5 * flash_p)
        wave_rect = wr.adjusted(-expand_dist, -expand_dist, expand_dist, expand_dist)
        wave_alpha = int(220 * flash_intensity)
        if wave_alpha > 0 and wave_rect.width() > 0:
            pen = QPen(QColor(255, 0, 40, wave_alpha), PIXEL_SIZE * 2)
            painter.setPen(pen)
            painter.drawRect(wave_rect)

            if expand_dist > PIXEL_SIZE * 8:
                inner_dist = expand_dist - PIXEL_SIZE * 6
                inner_rect = wr.adjusted(-inner_dist, -inner_dist, inner_dist, inner_dist)
                pen2 = QPen(QColor(255, 45, 120, int(wave_alpha * 0.7)), PIXEL_SIZE)
                painter.setPen(pen2)
                painter.drawRect(inner_rect)

        dither_zone = wr.adjusted(
            -PIXEL_SIZE * 18, -PIXEL_SIZE * 18, PIXEL_SIZE * 18, PIXEL_SIZE * 18
        )
        dither_step = PIXEL_SIZE * 2
        dither_color = QColor(255, 0, 45, int(180 * flash_intensity))

        for y in range(dither_zone.top(), dither_zone.bottom(), dither_step):
            for x in range(dither_zone.left(), dither_zone.right(), dither_step):
                if wr.contains(x, y):
                    continue
                bx = (x // dither_step) % 4
                by = (y // dither_step) % 4
                threshold = BAYER_4X4[by][bx] / 16.0
                if flash_intensity > threshold:
                    painter.fillRect(x, y, dither_step, dither_step, dither_color)
