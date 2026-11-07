"""Полноэкранный оверлей анимаций перехода, перемещения и телепортации окна."""

from __future__ import annotations

import contextlib
import math
import random
from collections.abc import Callable

from PySide6.QtCore import QElapsedTimer, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QGuiApplication,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

from ..ui.speech_sfx import get_speech_sfx
from .transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_WHITE,
    DURATION_ERRATIC_MS,
    DURATION_IN_MS,
    DURATION_OUT_MS,
    DURATION_POINT_MS,
    PIXEL_SIZE,
    CyberPixelBolt,
    CyberPixelSpark,
    CyberTrailFragment,
    draw_glitch_text,
    draw_hazard_frame,
    draw_scan_sweep,
    draw_scanlines,
    draw_screen_glitch_bars,
    evaluate_bezier,
    evaluate_manhattan_path,
    evaluate_vortex,
    is_reduced_motion_enabled,
    nearest_offscreen_point,
    perimeter_circuit_points,
    pick_palette_color,
    random_offscreen_point,
    snap_pixel,
    with_alpha,
)
from .transition_modes import TransitionModesMixin


class TransitionOverlay(QWidget, TransitionModesMixin):
    """Оверлей кинематических переходов, телепортации и появления окна питомца."""

    finished = Signal()

    def __init__(
        self,
        screen_rect: QRect,
        window_rect: QRect,
        mode: str,
        _parent: QWidget | None = None,
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
        self._mode = mode
        self._target = target
        self._on_peak = on_peak
        self._target_point = target_point
        self._peak_called = False

        if mode in ("out", "stealth_enter"):
            self._duration_ms = DURATION_OUT_MS
        elif mode == "lightning_to_point":
            self._duration_ms = DURATION_POINT_MS
        elif mode == "erratic_in":
            self._duration_ms = DURATION_ERRATIC_MS
        elif mode == "stealth_exit":
            self._duration_ms = DURATION_IN_MS + 80
        else:
            self._duration_ms = DURATION_IN_MS

        self._progress = 0.0
        self._clock: QElapsedTimer | None = None
        self._last_elapsed = 0

        self._target_pixmap: QPixmap | None = None
        if (
            target is not None
            and target.width() > 0
            and target.height() > 0
        ):
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

        self._is_reduced_motion = is_reduced_motion_enabled()
        self._bolts: list[CyberPixelBolt] = []
        self._sparks: list[CyberPixelSpark] = []
        self._trail: list[CyberTrailFragment] = []

        local_screen = QRect(
            0, 0, self._screen_rect.width(), self._screen_rect.height()
        )
        if mode == "out":
            self._offscreen_point = nearest_offscreen_point(
                local_screen, self._local_window, margin=90
            )
        else:
            self._offscreen_point = random_offscreen_point(
                local_screen, self._local_window, margin=90
            )
        target_center = self._local_window.center()

        self._erratic_waypoints: list[QPoint] = []
        if mode == "erratic_in":
            p0 = (
                self._offscreen_point
                if target_point is None
                else (target_point - offset)
            )
            p2 = target_center
            num_jumps = random.randint(6, 9)
            screen_w = max(100, local_screen.width() - 80)
            screen_h = max(100, local_screen.height() - 80)
            self._erratic_waypoints = [p0]
            for _ in range(num_jumps):
                rx = snap_pixel(random.randint(40, screen_w))
                ry = snap_pixel(random.randint(40, screen_h))
                self._erratic_waypoints.append(QPoint(rx, ry))
            self._erratic_waypoints.append(p2)
        elif mode in ("in", "stealth_exit"):
            p0 = (
                self._offscreen_point
                if target_point is None
                else (target_point - offset)
            )
            p2 = target_center
        else:
            p0 = target_center
            p2 = (
                self._offscreen_point
                if target_point is None
                else (target_point - offset)
            )

        mid_x = (p0.x() + p2.x()) // 2
        mid_y = (p0.y() + p2.y()) // 2
        dx = p2.x() - p0.x()
        dy = p2.y() - p0.y()
        dist = max(1.0, math.hypot(dx, dy))
        nx = -dy / dist
        ny = dx / dist

        self._kinematic_style = random.choice(
            ("bezier", "bezier", "manhattan", "vortex", "dash")
        )
        max_curve = min(360, max(80, int(dist * 0.45)))
        sign = random.choice((-1, 1))
        curve_offset = sign * random.randint(30, max_curve)
        p1 = QPoint(
            int(mid_x + nx * curve_offset), int(mid_y + ny * curve_offset)
        )
        self._p0 = p0
        self._p1 = p1
        self._p2 = p2
        self._last_mass_center = p0
        self._manhattan_mid_t = random.uniform(0.35, 0.65)
        self._manhattan_orientation = random.choice((0, 1))
        self._vortex_turns = random.uniform(1.2, 2.5) * random.choice(
            (-1.0, 1.0)
        )
        self._vortex_radius = min(
            240.0, max(40.0, dist * random.uniform(0.18, 0.38))
        )

        duration_factor = 1.0
        if self._kinematic_style == "dash":
            duration_factor = random.uniform(0.68, 0.82)
        elif self._kinematic_style == "vortex":
            duration_factor = random.uniform(1.10, 1.30)
        elif self._kinematic_style == "manhattan":
            duration_factor = random.uniform(0.95, 1.15)
        else:
            duration_factor = random.uniform(0.85, 1.15)
        self._duration_ms = max(
            200, int(self._duration_ms * duration_factor)
        )

        if (
            mode == "lightning_to_point"
            and self._local_target_point is not None
        ):
            starts = perimeter_circuit_points(self._local_window, 6)
            for s in starts:
                self._bolts.append(
                    CyberPixelBolt(
                        s,
                        self._local_target_point,
                        branch_chance=0.0,
                    )
                )

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        wh = self.windowHandle()
        if wh is not None:
            center = self._screen_rect.center()
            for scr in QGuiApplication.screens():
                if (
                    scr.geometry() == self._screen_rect
                    or scr.geometry().contains(center)
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

        peak_threshold = {
            "out": 0.35,
            "in": 0.65,
            "erratic_in": 0.72,
            "lightning_to_point": 0.62,
            "stealth_enter": 0.85,
            "stealth_exit": 0.85,
        }.get(self._mode, 0.50)
        if p >= peak_threshold and not self._peak_called:
            self._peak_called = True
            try:
                sfx = get_speech_sfx()
                if self._mode in ("in", "erratic_in"):
                    sfx.play_lightning_strike()
                elif self._mode == "lightning_to_point":
                    sfx.play_lightning_zap()
            except Exception:
                pass
            if self._on_peak is not None:
                with contextlib.suppress(Exception):
                    self._on_peak()
            if self._mode == "out" and self._target is not None:
                with contextlib.suppress(Exception):
                    self._target.hide()

        wr = self._local_window
        cx = wr.center().x()
        cy = wr.center().y()

        current_center = wr.center()
        if not self._is_reduced_motion:
            if self._mode == "erratic_in":
                if p < 0.72 and len(self._erratic_waypoints) >= 2:
                    flight_t = min(1.0, p / 0.72)
                    total_segs = len(self._erratic_waypoints) - 1
                    seg_float = flight_t * total_segs
                    idx = min(int(seg_float), total_segs - 1)
                    sub_t = seg_float - idx
                    snap_t = sub_t**2.2 if sub_t < 0.8 else 1.0
                    p_a = self._erratic_waypoints[idx]
                    p_b = self._erratic_waypoints[idx + 1]
                    cur_x = int(p_a.x() + (p_b.x() - p_a.x()) * snap_t)
                    cur_y = int(p_a.y() + (p_b.y() - p_a.y()) * snap_t)
                    jitter_range = int(14 * (1.0 - flight_t) + 3)
                    current_center = QPoint(
                        cur_x
                        + random.randint(-jitter_range, jitter_range),
                        cur_y
                        + random.randint(-jitter_range, jitter_range),
                    )
                else:
                    current_center = wr.center()
            elif self._mode in (
                "in",
                "out",
                "stealth_enter",
                "stealth_exit",
            ):
                if self._mode == "in":
                    flight_t = min(1.0, p / 0.65)
                    jitter_factor = 1.0 - flight_t
                elif self._mode == "stealth_enter":
                    flight_t = min(
                        1.0, max(0.0, (p - 0.28) / (0.72 - 0.28))
                    )
                    jitter_factor = 1.0 - flight_t
                elif self._mode == "stealth_exit":
                    flight_t = min(
                        1.0, max(0.0, (p - 0.28) / (0.68 - 0.28))
                    )
                    jitter_factor = 1.0 - flight_t
                else:
                    if p >= 0.35:
                        flight_t = min(1.0, (p - 0.35) / 0.65)
                        jitter_factor = flight_t
                    else:
                        flight_t = 0.0
                        jitter_factor = 0.0

                if (self._mode == "out" and p < 0.35) or (
                    self._mode == "stealth_enter" and p < 0.28
                ):
                    current_center = self._p0
                elif self._mode == "stealth_enter" and p >= 0.72:
                    current_center = self._p2
                elif self._mode == "stealth_exit" and p < 0.28:
                    current_center = self._p0
                elif self._mode == "stealth_exit" and p >= 0.68:
                    current_center = self._p2
                else:
                    if self._kinematic_style == "dash":
                        smooth_t = flight_t**3 * (
                            flight_t * (6.0 * flight_t - 15.0) + 10.0
                        )
                        current_center = QPoint(
                            int(
                                self._p0.x()
                                + (self._p2.x() - self._p0.x()) * smooth_t
                            ),
                            int(
                                self._p0.y()
                                + (self._p2.y() - self._p0.y()) * smooth_t
                            ),
                        )
                    elif self._kinematic_style == "manhattan":
                        smooth_t = (
                            flight_t * flight_t * (3.0 - 2.0 * flight_t)
                        )
                        current_center = evaluate_manhattan_path(
                            self._p0,
                            self._p2,
                            self._manhattan_mid_t,
                            smooth_t,
                            self._manhattan_orientation,
                        )
                    elif self._kinematic_style == "vortex":
                        smooth_t = (
                            flight_t * flight_t * (3.0 - 2.0 * flight_t)
                        )
                        current_center = evaluate_vortex(
                            self._p0,
                            self._p2,
                            smooth_t,
                            self._vortex_turns,
                            self._vortex_radius,
                        )
                    else:
                        smooth_t = (
                            flight_t * flight_t * (3.0 - 2.0 * flight_t)
                        )
                        current_center = evaluate_bezier(
                            self._p0, self._p1, self._p2, smooth_t
                        )

                    jitter_range = int(5 * jitter_factor)
                    if jitter_range > 0:
                        current_center = QPoint(
                            current_center.x()
                            + random.randint(-jitter_range, jitter_range),
                            current_center.y()
                            + random.randint(-jitter_range, jitter_range),
                        )

        self._last_mass_center = current_center

        is_flying = (
            (
                self._mode in ("in", "erratic_in")
                and p < (0.75 if self._mode == "erratic_in" else 0.70)
            )
            or (self._mode == "out" and p >= 0.30)
            or (
                self._mode in ("stealth_enter", "stealth_exit")
                and 0.28 <= p <= 0.72
            )
        )
        if is_flying and not self._is_reduced_motion:
            for _ in range(random.randint(1, 3)):
                ox = random.randint(-8, 8)
                oy = random.randint(-8, 8)
                fw = snap_pixel(random.randint(PIXEL_SIZE, PIXEL_SIZE * 3))
                fh = snap_pixel(
                    random.choice((PIXEL_SIZE, PIXEL_SIZE * 2))
                )
                c = pick_palette_color()
                self._trail.append(
                    CyberTrailFragment(
                        current_center.x() + ox - fw // 2,
                        current_center.y() + oy - fh // 2,
                        fw,
                        fh,
                        c,
                        life=random.uniform(0.20, 0.44),
                    )
                )

        self._trail = [tr for tr in self._trail if tr.step(dt)]

        if self._mode == "out":
            is_flash_active = 0.24 <= p <= 0.88
        elif self._mode == "lightning_to_point":
            is_flash_active = 0.30 <= p <= 0.96
        else:
            is_flash_active = 0.20 <= p <= 0.86

        if is_flash_active:
            for _ in range(9):
                angle = random.uniform(0, math.tau)
                speed = random.uniform(110.0, 720.0)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                if (
                    self._mode == "lightning_to_point"
                    and self._local_target_point
                ):
                    base = QPoint(self._local_target_point)
                    spread_x = wr.width() // 2
                    spread_y = wr.height() // 2
                else:
                    base = QPoint(cx, cy)
                    spread_x = wr.width() // 3
                    spread_y = wr.height() // 3
                sx = base.x() + random.randint(-spread_x, spread_x)
                sy = base.y() + random.randint(-spread_y, spread_y)

                kind = random.choice(("spark", "bit", "bar", "bit"))
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
                        life=random.uniform(0.18, 0.46),
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

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        p = self._progress
        wr = self._local_window

        self._paint_screen_layer(painter, p)

        if self._mode == "out":
            self._paint_out(painter, p, wr)
        elif self._mode == "stealth_enter":
            self._paint_stealth_enter(painter, p, wr)
        elif self._mode == "stealth_exit":
            self._paint_stealth_exit(painter, p, wr)
        elif self._mode == "lightning_to_point":
            if self._local_target_point is not None:
                self._paint_lightning_to_point(
                    painter, p, wr, self._local_target_point
                )
        else:
            self._paint_in(painter, p, wr)

        painter.end()

    def _paint_screen_layer(self, painter: QPainter, p: float) -> None:

        full = self.rect()
        draw_scanlines(painter, full, alpha=26, spacing=4)

        if self._mode == "out":
            intensity = max(0.15, 1.0 - p * 0.75)
            draw_screen_glitch_bars(painter, full, p, intensity)
            draw_hazard_frame(
                painter, full, intensity=max(0.0, 1.0 - p / 0.72)
            )
            draw_scan_sweep(painter, full, p * 1.35, COLOR_CRIMSON)
            draw_glitch_text(
                painter,
                28,
                36,
                "RELIC // SIGNAL DEGRADED",
                COLOR_CRIMSON,
                11,
            )
            draw_glitch_text(
                painter, 28, 52, "OPTICS OFFLINE", COLOR_WHITE, 9
            )
        elif self._mode in ("in", "erratic_in"):
            intensity = 0.18 + 0.45 * max(0.0, 1.0 - abs(p - 0.3) / 0.3)
            draw_screen_glitch_bars(painter, full, p, intensity)
            draw_scan_sweep(
                painter, full, (p * 1.25) % 1.0, COLOR_ACID_GREEN
            )
            draw_glitch_text(
                painter,
                28,
                36,
                "KIROSHI OPTICS // BOOT"
                if self._mode == "in"
                else "ROGUE SIGNAL // ANOMALY",
                COLOR_ACID_GREEN,
                10,
            )
            draw_glitch_text(
                painter,
                28,
                52,
                "CAPRI LINK ESTABLISHED"
                if p > 0.45
                else "UPLINK HANDSHAKE...",
                COLOR_WHITE,
                9,
            )
        else:
            draw_screen_glitch_bars(painter, full, p, 0.35 + 0.35 * p)
            draw_scan_sweep(
                painter, full, (p * 1.1) % 1.0, COLOR_ACID_GREEN
            )
            draw_glitch_text(
                painter,
                28,
                36,
                "BREACH PROTOCOL // TRACE",
                COLOR_ACID_GREEN,
                10,
            )
            draw_glitch_text(
                painter, 28, 52, "CURSOR LOCK 100%", COLOR_WHITE, 9
            )

        marker = with_alpha(COLOR_WHITE, 150)
        for x, y in (
            (full.left() + 12, full.top() + 12),
            (full.right() - 30, full.top() + 12),
            (full.left() + 12, full.bottom() - 30),
            (full.right() - 30, full.bottom() - 30),
        ):
            painter.fillRect(x, y, 18, 1, marker)
            painter.fillRect(x, y, 1, 18, marker)

    def _panel_rect(
        self,
        anchor: QRect,
        width: int = 224,
        height: int = 32,
        prefer_below: bool = False,
    ) -> QRect:

        width = max(160, min(width, self.width() - 16))
        x = anchor.center().x() - width // 2
        x = max(8, min(x, self.width() - width - 8))
        if prefer_below:
            y = anchor.bottom() + 14
            if y + height > self.height() - 8:
                y = max(8, anchor.top() - height - 14)
        else:
            y = anchor.top() - height - 14
            if y < 8:
                y = anchor.bottom() + 14
        y = max(8, min(y, self.height() - height - 8))
        return QRect(x, y, width, height)

    def _panel_near_point(
        self, point: QPoint, width: int = 224, height: int = 32
    ) -> QRect:
        x = point.x() - width // 2
        x = max(8, min(x, self.width() - width - 8))
        y = point.y() + 78
        if y + height > self.height() - 8:
            y = max(8, point.y() - height - 78)
        return QRect(x, y, width, height)
