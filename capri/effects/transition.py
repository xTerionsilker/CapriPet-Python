from __future__ import annotations

import math
import random
from typing import Callable, List

from PySide6.QtCore import QElapsedTimer, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from .transition_fx import (
    BAYER_4X4,
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    DURATION_IN_MS,
    DURATION_OUT_MS,
    DURATION_POINT_MS,
    DURATION_ERRATIC_MS,
    PIXEL_SIZE,
    CyberKiroshiReticle,
    CyberPixelBolt,
    CyberPixelSpark,
    CyberShockwaveRing,
    CyberTrailFragment,
    draw_breach_grid,
    draw_glitch_mass,
    draw_glitch_text,
    draw_hazard_frame,
    draw_hex_stream,
    draw_quickhack_panel,
    draw_scan_sweep,
    draw_scanlines,
    draw_screen_glitch_bars,
    evaluate_bezier,
    is_reduced_motion_enabled,
    nearest_offscreen_point,
    perimeter_circuit_points,
    pick_palette_color,
    random_offscreen_point,
    snap_pixel,
    snap_point,
    with_alpha,
)
from ..ui.speech_sfx import get_speech_sfx

class TransitionOverlay(QWidget):
\
\
\
\
\

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
        self._mode = mode
        self._target = target
        self._on_peak = on_peak
        self._target_point = target_point
        self._peak_called = False

        if mode == "out":
            self._duration_ms = DURATION_OUT_MS
        elif mode == "lightning_to_point":
            self._duration_ms = DURATION_POINT_MS
        elif mode == "erratic_in":
            self._duration_ms = DURATION_ERRATIC_MS
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

        self._is_reduced_motion = is_reduced_motion_enabled()
        self._bolts: List[CyberPixelBolt] = []
        self._sparks: List[CyberPixelSpark] = []
        self._trail: List[CyberTrailFragment] = []

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

        self._erratic_waypoints: List[QPoint] = []
        if mode == "erratic_in":
            p0 = self._offscreen_point if target_point is None else (target_point - offset)
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
        elif mode == "in":
            p0 = self._offscreen_point if target_point is None else (target_point - offset)
            p2 = target_center
        else:
            p0 = target_center
            p2 = self._offscreen_point if target_point is None else (target_point - offset)

        mid_x = (p0.x() + p2.x()) // 2
        mid_y = (p0.y() + p2.y()) // 2
        dx = p2.x() - p0.x()
        dy = p2.y() - p0.y()
        dist = max(1.0, math.hypot(dx, dy))
        nx = -dy / dist
        ny = dx / dist
        curve_offset = random.randint(-140, 140)
        p1 = QPoint(int(mid_x + nx * curve_offset), int(mid_y + ny * curve_offset))
        self._p0 = p0
        self._p1 = p1
        self._p2 = p2
        self._last_mass_center = p0

        if mode == "lightning_to_point" and self._local_target_point is not None:
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

        peak_threshold = {
            "out": 0.35,
            "in": 0.65,
            "erratic_in": 0.72,
            "lightning_to_point": 0.62,
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

        current_center = wr.center()
        if not self._is_reduced_motion:
            if self._mode == "erratic_in":
                if p < 0.72 and len(self._erratic_waypoints) >= 2:
                    flight_t = min(1.0, p / 0.72)
                    total_segs = len(self._erratic_waypoints) - 1
                    seg_float = flight_t * total_segs
                    idx = min(int(seg_float), total_segs - 1)
                    sub_t = seg_float - idx
                    # Fast aggressive snap between random screen nodes with micro-dwell
                    snap_t = sub_t ** 2.2 if sub_t < 0.8 else 1.0
                    p_a = self._erratic_waypoints[idx]
                    p_b = self._erratic_waypoints[idx + 1]
                    cur_x = int(p_a.x() + (p_b.x() - p_a.x()) * snap_t)
                    cur_y = int(p_a.y() + (p_b.y() - p_a.y()) * snap_t)
                    jitter_range = int(14 * (1.0 - flight_t) + 3)
                    current_center = QPoint(
                        cur_x + random.randint(-jitter_range, jitter_range),
                        cur_y + random.randint(-jitter_range, jitter_range),
                    )
                else:
                    current_center = wr.center()
            elif self._mode == "in":
                flight_t = min(1.0, p / 0.65)
                smooth_t = flight_t * flight_t * (3.0 - 2.0 * flight_t)
                current_center = evaluate_bezier(self._p0, self._p1, self._p2, smooth_t)
                jitter_range = int(3 * (1.0 - smooth_t))
                if jitter_range > 0:
                    current_center = QPoint(
                        current_center.x() + random.randint(-jitter_range, jitter_range),
                        current_center.y() + random.randint(-jitter_range, jitter_range),
                    )
            elif self._mode == "out":
                if p >= 0.35:
                    flight_t = min(1.0, (p - 0.35) / 0.65)
                    smooth_t = flight_t * flight_t * (3.0 - 2.0 * flight_t)
                    current_center = evaluate_bezier(self._p0, self._p1, self._p2, smooth_t)
                    jitter_range = int(3 * flight_t)
                    if jitter_range > 0:
                        current_center = QPoint(
                            current_center.x() + random.randint(-jitter_range, jitter_range),
                            current_center.y() + random.randint(-jitter_range, jitter_range),
                        )
                else:
                    current_center = self._p0

        self._last_mass_center = current_center

        is_flying = (
            (self._mode in ("in", "erratic_in") and p < (0.75 if self._mode == "erratic_in" else 0.70))
            or (self._mode == "out" and p >= 0.30)
        )
        if is_flying and not self._is_reduced_motion:
            for _ in range(random.randint(1, 3)):
                ox = random.randint(-8, 8)
                oy = random.randint(-8, 8)
                fw = snap_pixel(random.randint(PIXEL_SIZE, PIXEL_SIZE * 3))
                fh = snap_pixel(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)))
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
                if self._mode == "lightning_to_point" and self._local_target_point:
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
                painter, 28, 36, "RELIC // SIGNAL DEGRADED", COLOR_CRIMSON, 11
            )
            draw_glitch_text(painter, 28, 52, "OPTICS OFFLINE", COLOR_WHITE, 9)
        elif self._mode in ("in", "erratic_in"):
            intensity = 0.18 + 0.45 * max(0.0, 1.0 - abs(p - 0.3) / 0.3)
            draw_screen_glitch_bars(painter, full, p, intensity)
            draw_scan_sweep(painter, full, (p * 1.25) % 1.0, COLOR_ACID_GREEN)
            draw_glitch_text(
                painter, 28, 36, "KIROSHI OPTICS // BOOT" if self._mode == "in" else "ROGUE SIGNAL // ANOMALY", COLOR_ACID_GREEN, 10
            )
            draw_glitch_text(
                painter,
                28,
                52,
                "CAPRI LINK ESTABLISHED" if p > 0.45 else "UPLINK HANDSHAKE...",
                COLOR_WHITE,
                9,
            )
        else:
            draw_screen_glitch_bars(painter, full, p, 0.35 + 0.35 * p)
            draw_scan_sweep(painter, full, (p * 1.1) % 1.0, COLOR_ACID_GREEN)
            draw_glitch_text(
                painter, 28, 36, "BREACH PROTOCOL // TRACE", COLOR_ACID_GREEN, 10
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

    def _paint_in(self, painter: QPainter, p: float, wr: QRect) -> None:
        for tr in self._trail:
            tr.draw(painter)

        flight_cutoff = 0.72 if self._mode == "erratic_in" else 0.65
        if p < flight_cutoff:
            mass_center = self._last_mass_center
            intensity = 0.8 + 0.2 * math.sin(p * 25.0)
            base_sz = max(18, int(min(wr.width(), wr.height()) * 0.16))
            draw_glitch_mass(
                painter,
                mass_center,
                base_sz,
                intensity=intensity,
                seed=int(p * 1000) + mass_center.x() + mass_center.y(),
            )
        else:
            assembly_p = (p - flight_cutoff) / (1.0 - flight_cutoff)
            scale_overshoot = 1.0 + 0.08 * math.sin(assembly_p * math.pi)
            if assembly_p > 0.85:
                scale_overshoot = 1.0

            cur_w = max(1, int(wr.width() * scale_overshoot))
            cur_h = max(1, int(wr.height() * scale_overshoot))
            cur_rect = QRect(
                wr.center().x() - cur_w // 2,
                wr.center().y() - cur_h // 2,
                cur_w,
                cur_h,
            )

            rem = max(0.0, 1.0 - assembly_p)
            if rem > 0.02 and self._target_pixmap is not None:
                self._paint_pixel_matrix_assembly(painter, cur_rect, rem)

            if assembly_p < 0.5:
                draw_glitch_mass(
                    painter,
                    wr.center(),
                    int(min(wr.width(), wr.height()) * (0.16 + 0.35 * assembly_p)),
                    intensity=1.0 - assembly_p,
                    seed=int(p * 1000),
                )

            sweep_start = flight_cutoff + 0.05 * (1.0 - flight_cutoff)
            sweep_end = flight_cutoff + 0.85 * (1.0 - flight_cutoff)
            if sweep_start <= p <= sweep_end:
                sweep_p = (p - sweep_start) / max(0.01, sweep_end - sweep_start)
                y = cur_rect.top() + int(cur_rect.height() * sweep_p)
                painter.fillRect(
                    cur_rect.left(), y, cur_rect.width(), 2, with_alpha(COLOR_ACID_GREEN, 210)
                )

        flash_start = flight_cutoff - 0.03
        flash_end = min(1.0, flight_cutoff + 0.23)
        if flash_start <= p <= flash_end:
            flash_p = (p - flash_start) / max(0.01, flash_end - flash_start)
            self._paint_cyber_flash(painter, wr, flash_p, scheme="crimson")

        for spark in self._sparks:
            spark.draw(painter)

    def _paint_out(self, painter: QPainter, p: float, wr: QRect) -> None:
        for tr in self._trail:
            tr.draw(painter)

        if p < 0.35:
            collapse_p = p / 0.35
            scale = max(0.15, 1.0 - 0.85 * collapse_p)
            cur_w = max(1, int(wr.width() * scale))
            cur_h = max(1, int(wr.height() * scale))
            cur_rect = QRect(
                wr.center().x() - cur_w // 2,
                wr.center().y() - cur_h // 2,
                cur_w,
                cur_h,
            )

            if self._target_pixmap is not None:
                self._paint_pixel_matrix_assembly(painter, cur_rect, collapse_p)

            draw_glitch_mass(
                painter,
                wr.center(),
                int(min(wr.width(), wr.height()) * (0.35 - 0.19 * collapse_p)),
                intensity=collapse_p,
                seed=int(p * 1000),
            )
        else:
            mass_center = self._last_mass_center
            intensity = 0.8 + 0.2 * math.sin(p * 30.0)
            base_sz = max(18, int(min(wr.width(), wr.height()) * 0.16))
            draw_glitch_mass(
                painter,
                mass_center,
                base_sz,
                intensity=intensity,
                seed=int(p * 1000) + mass_center.x() + mass_center.y(),
            )

        if 0.25 <= p <= 0.55:
            flash_p = (p - 0.25) / 0.30
            self._paint_cyber_flash(painter, wr, flash_p, scheme="crimson")

        for spark in self._sparks:
            spark.draw(painter)

    def _paint_lightning_to_point(
        self, painter: QPainter, p: float, wr: QRect, target_pt: QPoint
    ) -> None:
        

        if p < 0.78:
            grid_rect = wr.adjusted(-28, -28, 28, 28)
            draw_breach_grid(
                painter,
                grid_rect,
                min(1.0, p / 0.55),
                seed=2077 + wr.center().x() + wr.center().y(),
                cell=10,
                color=COLOR_ACID_GREEN,
            )

        if p < 0.80:
            draw_hex_stream(
                painter,
                wr.adjusted(-52, -52, 52, 52),
                p,
                columns=max(6, wr.width() // 12),
                color=COLOR_ACID_GREEN,
            )

        if p <= 0.86:
            cursor_p = min(1.0, p / 0.22) * (1.0 - max(0.0, (p - 0.72) / 0.14))
            CyberKiroshiReticle.draw(
                painter,
                wr,
                cursor_p,
                color=COLOR_ACID_GREEN,
                rotation=-p * math.tau * 1.8,
                label="TRACE // ORIGIN",
                locked=True,
            )

        bolt_t = min(1.0, p / 0.58)
        fade = 1.0
        if p > 0.84:
            fade = max(0.0, 1.0 - (p - 0.84) / 0.16)
        painter.setOpacity(fade)
        for bolt in self._bolts:
            bolt.draw(painter, bolt_t)
        painter.setOpacity(1.0)

        self._paint_data_packets(painter, wr.center(), target_pt, p)

        if p >= 0.20:
            recv_p = min(1.0, (p - 0.20) / 0.60)
            target_rect = QRect(target_pt.x() - 62, target_pt.y() - 62, 124, 124)
            CyberKiroshiReticle.draw(
                painter,
                target_rect,
                recv_p,
                color=COLOR_CRIMSON,
                bracket_offset=int((1.0 - recv_p) * 46),
                rotation=p * math.tau * 1.3,
                label="CAPRI // LOCK",
                locked=p > 0.68,
            )
            panel = self._panel_near_point(target_pt, 228, 32)
            draw_quickhack_panel(
                painter,
                panel,
                min(1.0, (p - 0.20) / 0.68),
                color=COLOR_ACID_GREEN if p < 0.72 else COLOR_CRIMSON,
                title="TRACE ROUTE",
                status="LOCKING" if p < 0.72 else "LOCKED",
            )

        if p >= 0.55:
            flash_p = (p - 0.55) / 0.45
            radius = snap_pixel(int(96 * flash_p))
            CyberShockwaveRing.draw(
                painter, target_pt, radius, with_alpha(COLOR_CRIMSON, 220)
            )
            CyberShockwaveRing.draw(
                painter,
                target_pt,
                max(0, radius - 12),
                with_alpha(COLOR_WHITE, 200),
            )
            CyberShockwaveRing.draw(
                painter,
                target_pt,
                max(0, radius - 24),
                with_alpha(COLOR_ACID_GREEN, 150),
            )

        for spark in self._sparks:
            spark.draw(painter)

    def _paint_data_packets(
        self,
        painter: QPainter,
        start: QPoint,
        end: QPoint,
        p: float,
    ) -> None:
        
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        dist = max(1.0, math.hypot(dx, dy))
        nx = -dy / dist
        ny = dx / dist

        for lane, lane_color in (
            (-7, COLOR_ACID_GREEN),
            (0, COLOR_WHITE),
            (7, COLOR_CRIMSON),
        ):
            for i in range(4):
                t = (p * 1.9 + i * 0.25 + (0.08 if lane > 0 else 0.0)) % 1.0
                x = snap_pixel(start.x() + dx * t + nx * lane)
                y = snap_pixel(start.y() + dy * t + ny * lane)
                sz = PIXEL_SIZE * 2
                painter.fillRect(
                    x - sz // 2 - 2,
                    y - sz // 2 - 2,
                    sz + 4,
                    sz + 4,
                    with_alpha(COLOR_OBSIDIAN, 210),
                )
                painter.fillRect(
                    x - sz // 2,
                    y - sz // 2,
                    sz,
                    sz,
                    with_alpha(lane_color, 230),
                )
                if i == 0:
                    painter.fillRect(
                        x - PIXEL_SIZE // 2,
                        y - PIXEL_SIZE // 2,
                        PIXEL_SIZE,
                        PIXEL_SIZE,
                        COLOR_WHITE,
                    )

    def _paint_cyber_flash(
        self,
        painter: QPainter,
        wr: QRect,
        flash_p: float,
        scheme: str = "crimson",
    ) -> None:
\
\
\

        if flash_p <= 0.22:
            intensity = flash_p / 0.22
        else:
            intensity = max(0.0, 1.0 - (flash_p - 0.22) / 0.78) ** 1.6

        if intensity <= 0.01:
            return

        max_dim = max(wr.width(), wr.height())
        primary_neon = COLOR_CRIMSON if scheme == "crimson" else COLOR_ACID_GREEN
        secondary_neon = COLOR_ACID_GREEN if scheme == "crimson" else COLOR_CRIMSON

        screen_alpha = int(66 * intensity)
        if screen_alpha > 0:
            painter.fillRect(
                self.rect(), with_alpha(primary_neon, screen_alpha)
            )

        shift = PIXEL_SIZE * 2
        core_alpha = int(150 * intensity)
        bands = 7
        band_h = max(PIXEL_SIZE, wr.height() // bands)
        for i in range(bands):
            y = wr.top() + i * band_h
            h = min(band_h, wr.bottom() - y + 1)
            if h <= 0:
                continue
            band = QRect(wr.left(), y, wr.width(), h)
            painter.fillRect(
                band.translated(-shift, 0), with_alpha(COLOR_CRIMSON, core_alpha)
            )
            if i % 2 == 0:
                painter.fillRect(
                    band.translated(shift, 0),
                    with_alpha(COLOR_ACID_GREEN, int(core_alpha * 0.8)),
                )
            if i == 2:
                painter.fillRect(
                    band.translated(-shift * 3, 0),
                    with_alpha(COLOR_ELECTRIC_BLUE, int(core_alpha * 0.35)),
                )
            if i == bands - 2:
                painter.fillRect(
                    band.translated(shift * 3, 0),
                    with_alpha(COLOR_VIOLET, int(core_alpha * 0.28)),
                )
        painter.fillRect(wr, with_alpha(COLOR_WHITE, int(215 * intensity)))

        if intensity > 0.28:
            band_h = max(10, wr.height() // 10)
            for rect in (
                QRect(
                    wr.left() - PIXEL_SIZE * 8,
                    wr.top() - band_h,
                    wr.width() + PIXEL_SIZE * 16,
                    band_h,
                ),
                QRect(
                    wr.left() - PIXEL_SIZE * 8,
                    wr.bottom(),
                    wr.width() + PIXEL_SIZE * 16,
                    band_h,
                ),
            ):
                painter.fillRect(
                    rect, with_alpha(COLOR_OBSIDIAN, int(190 * intensity))
                )
                draw_hazard_frame(
                    painter, rect, intensity=intensity * 0.85, color=secondary_neon
                )

        wave_radius = snap_pixel(int(max_dim * 1.7 * flash_p))
        if wave_radius > PIXEL_SIZE * 2:
            wave_alpha = int(225 * intensity)
            CyberShockwaveRing.draw(
                painter,
                wr.center(),
                wave_radius,
                with_alpha(primary_neon, wave_alpha),
            )
            if wave_radius > PIXEL_SIZE * 8:
                CyberShockwaveRing.draw(
                    painter,
                    wr.center(),
                    wave_radius - PIXEL_SIZE * 6,
                    with_alpha(secondary_neon, int(wave_alpha * 0.7)),
                )

        dither_zone = wr.adjusted(
            -PIXEL_SIZE * 18,
            -PIXEL_SIZE * 18,
            PIXEL_SIZE * 18,
            PIXEL_SIZE * 18,
        )
        dither_step = PIXEL_SIZE * 2
        dither_color = with_alpha(COLOR_CRIMSON, int(165 * intensity))

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
        
        if wr.width() <= 0 or wr.height() <= 0:
            return

        w = wr.width()
        h = wr.height()
        left = wr.left()
        top = wr.top()

        if self._target_pixmap is not None and not self._target_pixmap.isNull():
            slice_count = int(10 + 44 * intensity)
            for _ in range(slice_count):
                sy = random.randint(0, max(0, h - PIXEL_SIZE * 2))
                sh = snap_pixel(random.randint(PIXEL_SIZE, PIXEL_SIZE * 4))
                sh = min(sh, h - sy)
                if sh <= 0:
                    continue
                shift_max = int((w // 4) * intensity)
                dx = snap_pixel(random.randint(-shift_max, shift_max))

                src = QRect(0, sy, w, sh)
                dst = QRect(left + dx, top + sy, w, sh)
                painter.drawPixmap(dst, self._target_pixmap, src)

                if intensity > 0.35 and random.random() < 0.32:
                    chroma_dx = dx + random.choice((-4, 4))
                    painter.setOpacity(0.35)
                    painter.drawPixmap(
                        QRect(left + chroma_dx, top + sy, w, sh),
                        self._target_pixmap,
                        src,
                    )
                    painter.setOpacity(1.0)

        bar_count = int(4 + 22 * intensity)
        for _ in range(bar_count):
            by = top + snap_pixel(random.randint(0, max(0, h - PIXEL_SIZE)))
            bh = snap_pixel(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)))
            col = with_alpha(
                pick_palette_color(), random.randint(140, 245)
            )
            painter.fillRect(left, by, w, bh, col)

        block_count = int(22 + 150 * intensity)
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
            col = with_alpha(pick_palette_color(), random.randint(155, 255))
            painter.fillRect(bx, by, bw, bh, col)
