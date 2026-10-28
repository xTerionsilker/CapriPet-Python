from __future__ import annotations

import math
import random
from typing import Callable, List

from PySide6.QtCore import QElapsedTimer, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from .transition_fx import (
    BAYER_4X4,
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
    DURATION_IN_MS,
    DURATION_OUT_MS,
    DURATION_POINT_MS,
    PIXEL_SIZE,
    CyberHoloReticle,
    CyberPixelBolt,
    CyberPixelSpark,
    CyberShockwaveRing,
    perimeter_circuit_points,
    pick_palette_color,
    screen_bus_points,
    snap_pixel,
)
from ..ui.speech_sfx import get_speech_sfx


class TransitionOverlay(QWidget):
    """
    Полноэкранный оверлей кибернетических переходов,
    выполненный строго в фирменной палитре Капри:
    #F20D2E (45%), #0B0B0B (35%), #3CF12B (16%), #FFFFFF (2%), #1E70F0 (1.5%), #9922EE (0.5%).
    """

    finished = Signal()

    def __init__(
        self,
        screen_rect: QRect,
        window_rect: QRect,
        mode: str,
        parent: QWidget | None = None,
        target: QWidget | None = None,
        on_peak: Callable[[], None] | None = None,
        target_point: QPoint | None = None,
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
        self._mode = mode  # "in", "out", или "lightning_to_point"
        self._target = target
        self._on_peak = on_peak
        self._target_point = target_point
        self._peak_called = False

        if mode == "out":
            self._duration_ms = DURATION_OUT_MS
        elif mode == "lightning_to_point":
            self._duration_ms = DURATION_POINT_MS
        else:
            self._duration_ms = DURATION_IN_MS

        self._progress = 0.0
        self._clock: QElapsedTimer | None = None
        self._last_elapsed = 0

        self._target_pixmap: QPixmap | None = None
        if target is not None and target.width() > 0 and target.height() > 0:
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

        offset = self._screen_rect.topLeft()
        self._local_window = self._window_rect.translated(-offset)
        self._local_target_point = (
            (target_point - offset) if target_point is not None else None
        )

        self._bolts: List[CyberPixelBolt] = []
        bolt_count = 36

        if mode == "lightning_to_point" and self._local_target_point is not None:
            # Направленные зеленые/алые шины от курсора к точке центра
            starts = perimeter_circuit_points(self._local_window, 14)
            for idx, s in enumerate(starts):
                scheme = "green" if idx % 2 == 0 else "crimson"
                self._bolts.append(
                    CyberPixelBolt(s, self._local_target_point, color_scheme=scheme)
                )
        elif mode == "out":
            # Разряды алого цвета (#F20D2E) взрываются наружу
            local_screen = QRect(
                0, 0, self._screen_rect.width(), self._screen_rect.height()
            )
            starts = perimeter_circuit_points(self._local_window, bolt_count)
            ends = screen_bus_points(local_screen, bolt_count)
            for idx, (s, e) in enumerate(zip(starts, ends)):
                scheme = "crimson" if idx % 3 != 0 else "green"
                self._bolts.append(CyberPixelBolt(s, e, color_scheme=scheme))
        else:
            # Разряды сходятся к силуэту (преимущественно #F20D2E и #3CF12B)
            local_screen = QRect(
                0, 0, self._screen_rect.width(), self._screen_rect.height()
            )
            starts = screen_bus_points(local_screen, bolt_count)
            ends = perimeter_circuit_points(self._local_window, bolt_count)
            for idx, (s, e) in enumerate(zip(starts, ends)):
                scheme = "crimson" if idx % 3 != 0 else "green"
                self._bolts.append(CyberPixelBolt(s, e, color_scheme=scheme))

        self._sparks: List[CyberPixelSpark] = []

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        wh = self.windowHandle()
        if wh is not None:
            center = self._screen_rect.center()
            for scr in QGuiApplication.screens():
                if scr.geometry() == self._screen_rect or scr.geometry().contains(
                    center
                ):
                    wh.setScreen(scr)
                    break

    def start(self) -> None:
        self._clock = QElapsedTimer()
        self._clock.start()
        self._last_elapsed = 0
        self.raise_()
        self.show()
        self._timer.start()
        try:
            sfx = get_speech_sfx()
            if self._mode == "out":
                sfx.play_lightning_strike()
            elif self._mode == "lightning_to_point":
                sfx.play_lightning_arc()
            else:
                sfx.play_lightning_arc()
        except Exception:
            pass

    def _tick(self) -> None:
        if self._clock is None:
            return
        elapsed = self._clock.elapsed()
        dt = max(0.001, (elapsed - self._last_elapsed) / 1000.0)
        self._last_elapsed = elapsed

        self._progress = min(1.0, elapsed / self._duration_ms)
        p = self._progress

        peak_threshold = 0.38 if self._mode == "out" else 0.44
        if p >= peak_threshold and not self._peak_called:
            self._peak_called = True
            try:
                sfx = get_speech_sfx()
                if self._mode == "in":
                    sfx.play_lightning_strike()
                elif self._mode == "lightning_to_point":
                    sfx.play_lightning_zap()
            except Exception:
                pass
            if self._on_peak is not None:
                try:
                    self._on_peak()
                except Exception:
                    pass
            if self._mode == "out" and self._target is not None:
                try:
                    self._target.hide()
                except Exception:
                    pass

        wr = self._local_window
        cx = wr.center().x()
        cy = wr.center().y()

        is_flash_active = (
            (0.30 <= p <= 0.85)
            if self._mode == "out"
            else (0.25 <= p <= 0.80)
        )
        if is_flash_active:
            for _ in range(7):
                angle = random.uniform(0, math.tau)
                speed = random.uniform(120.0, 650.0)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                sx = cx + random.randint(-wr.width() // 3, wr.width() // 3)
                sy = cy + random.randint(-wr.height() // 3, wr.height() // 3)

                kind = random.choice(("spark", "bit", "bar"))
                sz = (
                    PIXEL_SIZE
                    if kind == "spark"
                    else random.choice((PIXEL_SIZE, PIXEL_SIZE * 2))
                )
                self._sparks.append(
                    CyberPixelSpark(
                        sx,
                        sy,
                        vx,
                        vy,
                        color=pick_palette_color(),
                        size=sz,
                        life=random.uniform(0.20, 0.42),
                        kind=kind,
                    )
                )

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
        wr = self._local_window

        if self._mode == "out":
            self._paint_out(painter, p, wr)
        elif self._mode == "lightning_to_point":
            if self._local_target_point is not None:
                self._paint_lightning_to_point(
                    painter, p, wr, self._local_target_point
                )
        else:
            self._paint_in(painter, p, wr)

        painter.end()

    def _paint_in(self, painter: QPainter, p: float, wr: QRect) -> None:
        """Появление: сходящиеся кибер-шины, алый голографический прицел, вспышка перегрузки."""
        # 1. Голографический прицел (#F20D2E с обсидиановой тенью #0B0B0B)
        if p < 0.65:
            reticle_p = min(1.0, p / 0.45)
            offset = int((1.0 - reticle_p) * 75)
            CyberHoloReticle.draw(
                painter, wr, reticle_p, color=COLOR_CRIMSON, bracket_offset=offset
            )

        # 2. Кибер-шины сходятся к границам
        if p < 0.55:
            bolt_t = min(1.0, p / 0.38)
            for bolt in self._bolts:
                bolt.draw(painter, bolt_t)

        # 3. Кибернетическая вспышка перегрузки
        if 0.26 <= p <= 0.85:
            flash_p = (p - 0.26) / 0.59
            self._paint_cyber_flash(painter, wr, flash_p, scheme="crimson")

        # 4. Пиксельная сборка силуэта
        if p >= 0.45 and self._target_pixmap is not None:
            rem = max(0.0, 1.0 - (p - 0.45) / 0.55)
            if rem > 0.05:
                self._paint_pixel_matrix_assembly(painter, wr, rem)

        # 5. Частицы
        for spark in self._sparks:
            spark.draw(painter)

    def _paint_out(self, painter: QPainter, p: float, wr: QRect) -> None:
        """Исчезновение: пиксельный разрыв, вспышка, взрыв шин наружу, схлопывание в точку."""
        if p < 0.45 and self._target_pixmap is not None:
            tear_intensity = min(1.0, p / 0.38)
            self._paint_pixel_matrix_assembly(painter, wr, tear_intensity)

        if p < 0.42:
            CyberHoloReticle.draw(
                painter, wr, min(1.0, p / 0.30), color=COLOR_CRIMSON
            )

        if 0.30 <= p <= 0.85:
            flash_p = (p - 0.30) / 0.55
            self._paint_cyber_flash(painter, wr, flash_p, scheme="crimson")

        if p >= 0.35:
            bolt_t = min(1.0, (p - 0.35) / 0.45)
            if p > 0.85:
                fade = max(0.0, 1.0 - (p - 0.85) / 0.15)
                painter.setOpacity(fade)
            for bolt in self._bolts:
                bolt.draw(painter, bolt_t)
            painter.setOpacity(1.0)

        # ЭЛТ-схлопывание в лазерную линию (#FFFFFF ядро + #F20D2E ореол + #0B0B0B окантовка)
        if 0.40 <= p <= 0.72:
            collapse_p = (p - 0.40) / 0.32
            line_w = snap_pixel(max(PIXEL_SIZE * 2, int(wr.width() * (1.0 - collapse_p))))
            cx = wr.center().x()
            cy = wr.center().y()
            line_h = PIXEL_SIZE

            # Обсидиановый контрастный контур
            painter.fillRect(
                cx - line_w // 2,
                cy - line_h // 2 - 3,
                line_w,
                line_h + 6,
                COLOR_OBSIDIAN,
            )
            # Алый ореол (#F20D2E)
            painter.fillRect(
                cx - line_w // 2,
                cy - line_h // 2 - 1,
                line_w,
                line_h + 2,
                COLOR_CRIMSON,
            )
            # Белое ядро (#FFFFFF)
            painter.fillRect(
                cx - line_w // 2,
                cy - line_h // 2,
                line_w,
                line_h,
                COLOR_WHITE,
            )

        for spark in self._sparks:
            spark.draw(painter)

    def _paint_lightning_to_point(
        self, painter: QPainter, p: float, wr: QRect, target_pt: QPoint
    ) -> None:
        """Захват курсора: хакерский зеленый прицел (#3CF12B), силовой кабель и вспышка в центре."""
        # 1. Прицел на курсоре (зеленый #3CF12B 16%)
        if p <= 0.70:
            reticle_p = 1.0 - p / 0.70
            CyberHoloReticle.draw(
                painter, wr, reticle_p, color=COLOR_ACID_GREEN
            )

        # 2. Силовые кабели тянутся от курсора в центр
        bolt_t = min(1.0, p / 0.65)
        if p > 0.85:
            fade = max(0.0, 1.0 - (p - 0.85) / 0.15)
            painter.setOpacity(fade)
        for bolt in self._bolts:
            bolt.draw(painter, bolt_t)
        painter.setOpacity(1.0)

        # 3. Приемный вихрь в целевой точке (алый #F20D2E с белым ядром)
        if p >= 0.35:
            recv_p = (p - 0.35) / 0.65
            target_rect = QRect(
                target_pt.x() - 60, target_pt.y() - 60, 120, 120
            )
            offset = int((1.0 - recv_p) * 50)
            CyberHoloReticle.draw(
                painter,
                target_rect,
                recv_p,
                color=COLOR_CRIMSON,
                bracket_offset=offset,
            )
            if p >= 0.65:
                flash_p = (p - 0.65) / 0.35
                r = snap_pixel(int(80 * flash_p))
                CyberShockwaveRing.draw(painter, target_pt, r, COLOR_CRIMSON)
                CyberShockwaveRing.draw(
                    painter, target_pt, max(0, r - 12), COLOR_WHITE
                )

        for spark in self._sparks:
            spark.draw(painter)

    def _paint_cyber_flash(
        self,
        painter: QPainter,
        wr: QRect,
        flash_p: float,
        scheme: str = "crimson",
    ) -> None:
        """
        Кибернетическая вспышка: хроматическое смещение (#F20D2E / #3CF12B / #1E70F0),
        октагональные волны перегрузки и обсидиановый дизеринг.
        """
        if flash_p <= 0.22:
            intensity = flash_p / 0.22
        else:
            intensity = max(0.0, 1.0 - (flash_p - 0.22) / 0.78) ** 1.6

        if intensity <= 0.01:
            return

        max_dim = max(wr.width(), wr.height())

        primary_neon = COLOR_CRIMSON if scheme == "crimson" else COLOR_ACID_GREEN
        secondary_neon = COLOR_ACID_GREEN if scheme == "crimson" else COLOR_CRIMSON

        # 1. Фоновое неоновое мерцание экрана (#F20D2E 45%)
        screen_alpha = int(70 * intensity)
        if screen_alpha > 0:
            painter.fillRect(
                self.rect(),
                QColor(
                    primary_neon.red(),
                    primary_neon.green(),
                    primary_neon.blue(),
                    screen_alpha,
                ),
            )

        # 2. Хроматическое ядро вспышки:
        # Алый блок влево (#F20D2E), кислотно-зеленый/синий вправо (#3CF12B / #1E70F0)
        shift = PIXEL_SIZE * 2
        core_alpha = int(220 * intensity)
        painter.fillRect(
            wr.translated(-shift, 0),
            QColor(COLOR_CRIMSON.red(), COLOR_CRIMSON.green(), COLOR_CRIMSON.blue(), core_alpha),
        )
        painter.fillRect(
            wr.translated(shift, 0),
            QColor(
                COLOR_ACID_GREEN.red(),
                COLOR_ACID_GREEN.green(),
                COLOR_ACID_GREEN.blue(),
                core_alpha,
            ),
        )
        # Ослепительно белое ядро (#FFFFFF 2%)
        white_alpha = int(245 * intensity)
        painter.fillRect(wr, QColor(COLOR_WHITE.red(), COLOR_WHITE.green(), COLOR_WHITE.blue(), white_alpha))

        # 3. Расширяющиеся кибер-октагональные волны (#F20D2E и #0B0B0B)
        wave_radius = snap_pixel(int(max_dim * 1.6 * flash_p))
        if wave_radius > PIXEL_SIZE * 2:
            wave_alpha = int(230 * intensity)
            c1 = QColor(primary_neon)
            c1.setAlpha(wave_alpha)
            CyberShockwaveRing.draw(painter, wr.center(), wave_radius, c1)

            if wave_radius > PIXEL_SIZE * 8:
                c2 = QColor(secondary_neon)
                c2.setAlpha(int(wave_alpha * 0.7))
                CyberShockwaveRing.draw(
                    painter,
                    wr.center(),
                    wave_radius - PIXEL_SIZE * 6,
                    c2,
                )

        # 4. Пиксельный матричный дизеринг (Bayer Matrix с контрастом #0B0B0B)
        dither_zone = wr.adjusted(
            -PIXEL_SIZE * 16,
            -PIXEL_SIZE * 16,
            PIXEL_SIZE * 16,
            PIXEL_SIZE * 16,
        )
        dither_step = PIXEL_SIZE * 2
        dither_color = QColor(COLOR_CRIMSON)
        dither_color.setAlpha(int(170 * intensity))

        for y in range(dither_zone.top(), dither_zone.bottom(), dither_step):
            for x in range(dither_zone.left(), dither_zone.right(), dither_step):
                if wr.contains(x, y):
                    continue
                bx = (x // dither_step) % 4
                by = (y // dither_step) % 4
                threshold = BAYER_4X4[by][bx] / 16.0
                if intensity > threshold:
                    painter.fillRect(
                        x, y, dither_step, dither_step, dither_color
                    )

    def _paint_pixel_matrix_assembly(
        self, painter: QPainter, wr: QRect, intensity: float
    ) -> None:
        """Пиксельная матричная сборка/разборка спрайта в фирменной палитре Капри."""
        if wr.width() <= 0 or wr.height() <= 0:
            return

        w = wr.width()
        h = wr.height()
        left = wr.left()
        top = wr.top()

        if self._target_pixmap is not None and not self._target_pixmap.isNull():
            slice_count = int(10 + 36 * intensity)
            for _ in range(slice_count):
                sy = random.randint(0, max(0, h - PIXEL_SIZE * 2))
                sh = snap_pixel(random.randint(PIXEL_SIZE, PIXEL_SIZE * 4))
                sh = min(sh, h - sy)
                if sh <= 0:
                    continue
                shift_max = int((w // 5) * intensity)
                dx = snap_pixel(random.randint(-shift_max, shift_max))

                src = QRect(0, sy, w, sh)
                dst = QRect(left + dx, top + sy, w, sh)
                painter.drawPixmap(dst, self._target_pixmap, src)

        # Неоновые полосы по палитре Капри
        bar_count = int(4 + 20 * intensity)
        for _ in range(bar_count):
            by = top + snap_pixel(random.randint(0, max(0, h - PIXEL_SIZE)))
            bh = snap_pixel(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)))
            col = QColor(pick_palette_color())
            col.setAlpha(random.randint(150, 240))
            painter.fillRect(left, by, w, bh, col)

        # Цифровые пиксельные блоки (байты шума)
        block_count = int(20 + 130 * intensity)
        for _ in range(block_count):
            bx = left + snap_pixel(random.randint(0, max(0, w - PIXEL_SIZE)))
            by = top + snap_pixel(random.randint(0, max(0, h - PIXEL_SIZE)))
            bw = snap_pixel(
                random.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 4))
            )
            bh = snap_pixel(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)))
            bw = min(bw, wr.right() - bx + 1)
            bh = min(bh, wr.bottom() - by + 1)
            if bw <= 0 or bh <= 0:
                continue
            col = QColor(pick_palette_color())
            col.setAlpha(random.randint(160, 255))
            painter.fillRect(bx, by, bw, bh, col)
