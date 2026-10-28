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
    PIXEL_SIZE,
    CyberKiroshiReticle,
    CyberPixelBolt,
    CyberPixelSpark,
    CyberShockwaveRing,
    draw_breach_grid,
    draw_glitch_text,
    draw_hazard_frame,
    draw_hex_stream,
    draw_quickhack_panel,
    draw_scan_sweep,
    draw_scanlines,
    draw_screen_glitch_bars,
    perimeter_circuit_points,
    pick_palette_color,
    screen_bus_points,
    snap_pixel,
    with_alpha,
)
from ..ui.speech_sfx import get_speech_sfx


def _bolt_scheme(index: int, primary: str = "crimson") -> str:
    """Все разряды строго красно-чёрные, без зелёных и синих каналов."""
    return "crimson"


class TransitionOverlay(QWidget):
    """
    Полноэкранный оверлей кибернетических переходов в духе Cyberpunk 2077:
    Kiroshi-оптика, quickhack-панели, Breach Protocol, datamosh и ЭЛТ-схлопывание.
    Палитра строго фирменная:
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
        bolt_count = 10
        local_screen = QRect(
            0, 0, self._screen_rect.width(), self._screen_rect.height()
        )
        # Локальные шины вокруг силуэта — эффект остаётся сфокусированным на Капри,
        # а не превращает весь монитор в кашу из линий.
        outer_ring = self._local_window.adjusted(-320, -320, 320, 320)

        if mode == "lightning_to_point" and self._local_target_point is not None:
            # Трассировка: пакеты данных тянутся от курсора к центру экрана
            starts = perimeter_circuit_points(self._local_window, 6)
            for idx, s in enumerate(starts):
                scheme = _bolt_scheme(idx, primary="green")
                self._bolts.append(
                    CyberPixelBolt(
                        s,
                        self._local_target_point,
                        color_scheme=scheme,
                        branch_chance=0.0,
                    )
                )
        elif mode == "out":
            # Аварийный разрыв: короткие разряды вырываются из силуэта наружу
            starts = perimeter_circuit_points(self._local_window, bolt_count)
            ends = perimeter_circuit_points(outer_ring, bolt_count)
            for idx, (s, e) in enumerate(zip(starts, ends)):
                self._bolts.append(
                    CyberPixelBolt(
                        s,
                        e,
                        color_scheme=_bolt_scheme(idx, "crimson"),
                        branch_chance=0.08,
                    )
                )
            # Пара дальних аварийных шин к границам экрана
            for idx, (s, e) in enumerate(
                zip(
                    perimeter_circuit_points(outer_ring, 3),
                    screen_bus_points(local_screen, 3),
                )
            ):
                self._bolts.append(
                    CyberPixelBolt(
                        s,
                        e,
                        color_scheme=_bolt_scheme(idx, "crimson"),
                        branch_chance=0.10,
                    )
                )
        else:
            # Материализация: шины сходятся к силуэту из ближней зоны
            starts = perimeter_circuit_points(outer_ring, bolt_count)
            ends = perimeter_circuit_points(self._local_window, bolt_count)
            for idx, (s, e) in enumerate(zip(starts, ends)):
                self._bolts.append(
                    CyberPixelBolt(
                        s,
                        e,
                        color_scheme=_bolt_scheme(idx, "crimson"),
                        branch_chance=0.08,
                    )
                )
            # Редкие дальние пакеты из углов экрана
            for idx, (s, e) in enumerate(
                zip(
                    screen_bus_points(local_screen, 3),
                    perimeter_circuit_points(outer_ring, 3),
                )
            ):
                self._bolts.append(
                    CyberPixelBolt(
                        s,
                        e,
                        color_scheme=_bolt_scheme(idx, "green"),
                        branch_chance=0.10,
                    )
                )

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

        peak_threshold = {
            "out": 0.40,
            "in": 0.46,
            "lightning_to_point": 0.62,
        }.get(self._mode, 0.44)
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

    def paintEvent(self, _event) -> None:  # noqa: N802
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

    # ------------------------------------------------------------------
    # Общие экранные слои
    # ------------------------------------------------------------------

    def _paint_screen_layer(self, painter: QPainter, p: float) -> None:
        """ЭЛТ-развёртка, сбои кадра и служебная телеметрия поверх всего экрана."""
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
        elif self._mode == "in":
            intensity = 0.18 + 0.45 * max(0.0, 1.0 - abs(p - 0.3) / 0.3)
            draw_screen_glitch_bars(painter, full, p, intensity)
            draw_scan_sweep(painter, full, (p * 1.25) % 1.0, COLOR_ACID_GREEN)
            draw_glitch_text(
                painter, 28, 36, "KIROSHI OPTICS // BOOT", COLOR_ACID_GREEN, 10
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

        # Угловые метки оптики
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
        """Размещает HUD-панель рядом с якорем, не выходя за границы экрана."""
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

    # ------------------------------------------------------------------
    # Появление
    # ------------------------------------------------------------------

    def _paint_in(self, painter: QPainter, p: float, wr: QRect) -> None:
        """Появление: Kiroshi-оптика, quickhack-материализация и сборка силуэта."""
        # 1. Прицел Kiroshi закрывается на силуэте
        if p < 0.80:
            reticle_p = min(1.0, p / 0.48)
            offset = int((1.0 - reticle_p) * 92)
            CyberKiroshiReticle.draw(
                painter,
                wr,
                reticle_p,
                color=COLOR_CRIMSON,
                bracket_offset=offset,
                rotation=p * math.tau * 1.15,
                label="CAPRI // UPLINK",
                locked=p > 0.36,
            )

        # 2. Шины данных сходятся к границам спрайта
        if p < 0.70:
            bolt_t = min(1.0, p / 0.44)
            for bolt in self._bolts:
                bolt.draw(painter, bolt_t)

        # 3. Панель материализации
        if 0.04 <= p <= 0.96:
            panel = self._panel_rect(wr, 232, 32)
            draw_quickhack_panel(
                painter,
                panel,
                min(1.0, p / 0.72),
                color=COLOR_CRIMSON,
                title="CAPRI.EXE",
                status="MATERIALIZE",
            )

        # 4. Пиксельная сборка с datamosh-разрывами
        if p >= 0.30 and self._target_pixmap is not None:
            rem = max(0.0, 1.0 - (p - 0.30) / 0.70)
            if rem > 0.04:
                self._paint_pixel_matrix_assembly(painter, wr, rem)

        # 5. Зелёный луч сканирует собирающийся силуэт
        if 0.34 <= p <= 0.92:
            sweep_p = (p - 0.34) / 0.58
            y = wr.top() + int(wr.height() * sweep_p)
            painter.fillRect(
                wr.left(), y, wr.width(), 2, with_alpha(COLOR_ACID_GREEN, 210)
            )
            painter.fillRect(
                wr.left(), y - 2, wr.width(), 1, with_alpha(COLOR_WHITE, 150)
            )

        # 6. Вспышка перегрузки
        if 0.22 <= p <= 0.84:
            flash_p = (p - 0.22) / 0.62
            self._paint_cyber_flash(painter, wr, flash_p, scheme="crimson")

        # 7. Октагональная ударная волна
        if p >= 0.42:
            wave_p = min(1.0, (p - 0.42) / 0.58)
            radius = snap_pixel(
                int(min(wr.width(), wr.height()) * 0.85 * wave_p)
            )
            if radius > PIXEL_SIZE * 2:
                CyberShockwaveRing.draw(
                    painter,
                    wr.center(),
                    radius,
                    with_alpha(COLOR_CRIMSON, int(210 * (1.0 - wave_p) + 30)),
                )
                CyberShockwaveRing.draw(
                    painter,
                    wr.center(),
                    max(0, radius - PIXEL_SIZE * 6),
                    with_alpha(COLOR_ACID_GREEN, int(120 * (1.0 - wave_p))),
                )

        for spark in self._sparks:
            spark.draw(painter)

    # ------------------------------------------------------------------
    # Исчезновение
    # ------------------------------------------------------------------

    def _paint_out(self, painter: QPainter, p: float, wr: QRect) -> None:
        """Исчезновение: Relic-сбой, datamosh, аварийные шины и ЭЛТ-схлопывание."""
        # 1. Спрайт разъезжается цифровыми срезами
        if p < 0.38 and self._target_pixmap is not None:
            tear_intensity = min(1.0, p / 0.34)
            self._paint_pixel_matrix_assembly(painter, wr, tear_intensity)

        # 2. Прицел теряет цель
        if p < 0.52:
            CyberKiroshiReticle.draw(
                painter,
                wr,
                min(1.0, p / 0.34),
                color=COLOR_CRIMSON,
                rotation=-p * math.tau * 1.4,
                label="SIGNAL LOST",
                locked=False,
            )

        # 3. Панель аварийного отключения
        if p <= 0.72:
            panel = self._panel_rect(wr, 232, 32)
            draw_quickhack_panel(
                painter,
                panel,
                max(0.0, 1.0 - p / 0.62),
                color=COLOR_CRIMSON,
                title="CAPRI.EXE",
                status="DISCONNECT",
            )

        # 4. Вспышка перегрузки
        if 0.22 <= p <= 0.82:
            flash_p = (p - 0.22) / 0.60
            self._paint_cyber_flash(painter, wr, flash_p, scheme="crimson")

        # 5. Разряды вырываются наружу
        if p >= 0.26:
            bolt_t = min(1.0, (p - 0.26) / 0.45)
            fade = 1.0
            if p > 0.80:
                fade = max(0.0, 1.0 - (p - 0.80) / 0.20)
            painter.setOpacity(fade)
            for bolt in self._bolts:
                bolt.draw(painter, bolt_t)
            painter.setOpacity(1.0)

        # 6. ЭЛТ-схлопывание в лазерную линию
        if 0.36 <= p <= 0.74:
            collapse_p = (p - 0.36) / 0.38
            line_w = snap_pixel(
                max(PIXEL_SIZE * 2, int(wr.width() * (1.0 - collapse_p)))
            )
            cx = wr.center().x()
            cy = wr.center().y()
            line_h = PIXEL_SIZE

            painter.fillRect(
                cx - line_w // 2,
                cy - line_h // 2 - 4,
                line_w,
                line_h + 8,
                COLOR_OBSIDIAN,
            )
            painter.fillRect(
                cx - line_w // 2,
                cy - line_h // 2 - 2,
                line_w,
                line_h + 4,
                COLOR_CRIMSON,
            )
            painter.fillRect(
                cx - line_w // 2,
                cy - line_h // 2 - 1,
                line_w,
                line_h + 2,
                COLOR_ACID_GREEN,
            )
            painter.fillRect(
                cx - line_w // 2,
                cy - line_h // 2,
                line_w,
                line_h,
                COLOR_WHITE,
            )

        # 7. Красная волна разрыва
        if p >= 0.42:
            wave_p = min(1.0, (p - 0.42) / 0.58)
            radius = snap_pixel(int(self.width() * 0.55 * wave_p))
            if radius > PIXEL_SIZE * 2:
                CyberShockwaveRing.draw(
                    painter,
                    wr.center(),
                    radius,
                    with_alpha(COLOR_CRIMSON, int(180 * (1.0 - wave_p))),
                )

        for spark in self._sparks:
            spark.draw(painter)

    # ------------------------------------------------------------------
    # Захват курсора
    # ------------------------------------------------------------------

    def _paint_lightning_to_point(
        self, painter: QPainter, p: float, wr: QRect, target_pt: QPoint
    ) -> None:
        """Захват курсора: Breach Protocol, трассировка и материализация Капри в центре."""
        # 1. Матрица Breach Protocol вокруг курсора
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

        # 2. Поток глифов вокруг курсора
        if p < 0.80:
            draw_hex_stream(
                painter,
                wr.adjusted(-52, -52, 52, 52),
                p,
                columns=max(6, wr.width() // 12),
                color=COLOR_ACID_GREEN,
            )

        # 3. Прицел на курсоре
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

        # 4. Силовые кабели тянутся от курсора в центр
        bolt_t = min(1.0, p / 0.58)
        fade = 1.0
        if p > 0.84:
            fade = max(0.0, 1.0 - (p - 0.84) / 0.16)
        painter.setOpacity(fade)
        for bolt in self._bolts:
            bolt.draw(painter, bolt_t)
        painter.setOpacity(1.0)

        self._paint_data_packets(painter, wr.center(), target_pt, p)

        # 5. Приёмный прицел и панель быстрого взлома в целевой точке
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

        # 6. Финал: вспышка и ударная волна
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
        """Пакеты данных, бегущие по каналу от курсора к цели."""
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

    # ------------------------------------------------------------------
    # Вспышка и цифровая разборка
    # ------------------------------------------------------------------

    def _paint_cyber_flash(
        self,
        painter: QPainter,
        wr: QRect,
        flash_p: float,
        scheme: str = "crimson",
    ) -> None:
        """
        Перегрузка оптики: хроматическое расслоение, срезанные панели,
        октагональные волны и обсидиановый дизеринг.
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

        # 1. Красная засветка экрана
        screen_alpha = int(66 * intensity)
        if screen_alpha > 0:
            painter.fillRect(
                self.rect(), with_alpha(primary_neon, screen_alpha)
            )

        # 2. Хроматическое ядро вспышки: горизонтальные datamosh-срезы,
        # а не сплошные цветные прямоугольники.
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

        # 3. Срезанные аварийные панели по краям экрана
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

        # 4. Октагональные волны
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

        # 5. Bayer-дизеринг вокруг силуэта
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
        """Datamosh-разборка спрайта: срезы, хроматический сдвиг и цифровые блоки."""
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

                # Хроматический шлейф среза (редкий, чтобы не пересвечивать кадр)
                if intensity > 0.35 and random.random() < 0.32:
                    chroma_dx = dx + random.choice((-4, 4))
                    painter.setOpacity(0.35)
                    painter.drawPixmap(
                        QRect(left + chroma_dx, top + sy, w, sh),
                        self._target_pixmap,
                        src,
                    )
                    painter.setOpacity(1.0)

        # Неоновые полосы по палитре Капри
        bar_count = int(4 + 22 * intensity)
        for _ in range(bar_count):
            by = top + snap_pixel(random.randint(0, max(0, h - PIXEL_SIZE)))
            bh = snap_pixel(random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)))
            col = with_alpha(
                pick_palette_color(), random.randint(140, 245)
            )
            painter.fillRect(left, by, w, bh, col)

        # Цифровые пиксельные блоки (байты шума)
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
