"""Полноэкранный оверлей наведения на курсор мыши в стиле киберпанк."""

from __future__ import annotations

import contextlib
import math
import random
import time

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..effects.transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
    PIXEL_SIZE,
    CyberKiroshiReticle,
    draw_glitch_mass,
    pick_palette_color,
    snap_pixel,
    with_alpha,
)
from ..ui.speech_sfx import get_speech_sfx
from ..ui.theme import get_hud_font


def get_virtual_screen_geometry() -> QRect:
    screens = QGuiApplication.screens()
    if not screens:
        return QRect(0, 0, 1920, 1080)
    rect = screens[0].geometry()
    for scr in screens[1:]:
        rect = rect.united(scr.geometry())
    return rect


class CursorPointerOverlay(QWidget):
    """Оверлей с анимированной глитч-линией наведения и визиром захвата цели."""

    def __init__(self, parent: QWidget | None = None) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._start_pos: QPoint = QPoint(0, 0)
        self._target_pos: QPoint = QPoint(0, 0)

        self._start_time: float = 0.0
        self._state: str = "idle"
        self._build_progress: float = 0.0
        self._fade_progress: float = 1.0
        self._fade_start_time: float = 0.0
        self._frame: int = 0

        self._build_duration: float = 0.35
        self._fade_duration: float = 0.45

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._on_tick)

    def activate(self, start_pos: QPoint, target_pos: QPoint) -> None:
        self.setGeometry(get_virtual_screen_geometry())
        self._start_pos = start_pos
        self._target_pos = target_pos
        self._start_time = time.monotonic()
        self._state = "building"
        self._build_progress = 0.0
        self._fade_progress = 1.0
        self._frame = 0

        self.raise_()
        self.show()
        self._anim_timer.start()

        with contextlib.suppress(Exception):
            get_speech_sfx().play_swoosh()
        self.update()

    def update_positions(
        self, start_pos: QPoint, target_pos: QPoint
    ) -> None:
        self._start_pos = start_pos
        if self._target_pos != target_pos:
            self._target_pos = target_pos
            self.update()

    def start_fade_out(self) -> None:
        if self._state in ("fading", "idle"):
            return
        self._state = "fading"
        self._fade_start_time = time.monotonic()

    def deactivate(self) -> None:
        self._anim_timer.stop()
        self._state = "idle"
        self.hide()

    def _on_tick(self) -> None:
        now = time.monotonic()
        self._frame += 1

        if self._state == "building":
            elapsed = now - self._start_time
            self._build_progress = min(1.0, elapsed / self._build_duration)
            if self._build_progress >= 1.0:
                self._state = "active"

        elif self._state == "fading":
            elapsed = now - self._fade_start_time
            self._fade_progress = max(
                0.0, 1.0 - (elapsed / self._fade_duration)
            )
            if self._fade_progress <= 0.0:
                self.deactivate()
                return

        self.update()

    def paintEvent(self, _event) -> None:
        if self._state == "idle":
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        offset = self.geometry().topLeft()
        local_start = self._start_pos - offset
        local_target = self._target_pos - offset

        overall_alpha = self._fade_progress
        if overall_alpha <= 0.001:
            painter.end()
            return

        dx = local_target.x() - local_start.x()
        dy = local_target.y() - local_start.y()
        total_dist = math.hypot(dx, dy)

        draw_dist = total_dist * self._build_progress
        if total_dist > 0.001:
            curr_target_x = local_start.x() + (dx / total_dist) * draw_dist
            curr_target_y = local_start.y() + (dy / total_dist) * draw_dist
            perp_x = -dy / total_dist
            perp_y = dx / total_dist
        else:
            curr_target_x = local_start.x()
            curr_target_y = local_start.y()
            perp_x = 0.0
            perp_y = 1.0

        current_head = QPointF(curr_target_x, curr_target_y)
        now = time.monotonic()

        rng = random.Random(self._frame * 31 + int(now * 100))

        num_segments = max(4, int(draw_dist // 28))
        segment_points: list[QPointF] = []
        for i in range(num_segments + 1):
            ratio = i / num_segments
            base_x = (
                local_start.x() + (curr_target_x - local_start.x()) * ratio
            )
            base_y = (
                local_start.y() + (curr_target_y - local_start.y()) * ratio
            )
            if 0 < i < num_segments:
                jitter_val = (
                    rng.uniform(-5.0, 5.0) if rng.random() < 0.75 else 0.0
                )
                base_x += perp_x * jitter_val
                base_y += perp_y * jitter_val
            segment_points.append(QPointF(base_x, base_y))

        for color_shift, shift_val in (
            (COLOR_CRIMSON, 3.0),
            (COLOR_ELECTRIC_BLUE, -3.0),
            (COLOR_ACID_GREEN, 1.5),
        ):
            if rng.random() < 0.85:
                shift_pen = QPen(
                    with_alpha(color_shift, int(110 * overall_alpha)), 2
                )
                painter.setPen(shift_pen)
                for i in range(len(segment_points) - 1):
                    p1 = segment_points[i] + QPointF(
                        perp_x * shift_val, perp_y * shift_val
                    )
                    p2 = segment_points[i + 1] + QPointF(
                        perp_x * shift_val, perp_y * shift_val
                    )
                    painter.drawLine(p1, p2)

        glow_pen = QPen(
            with_alpha(COLOR_CRIMSON, int(80 * overall_alpha)), 6
        )
        glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(glow_pen)
        for i in range(len(segment_points) - 1):
            painter.drawLine(segment_points[i], segment_points[i + 1])

        core_pen = QPen(
            with_alpha(COLOR_WHITE, int(230 * overall_alpha)), 2
        )
        core_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(core_pen)
        for i in range(len(segment_points) - 1):
            painter.drawLine(segment_points[i], segment_points[i + 1])

        dot_pen = QPen(
            with_alpha(COLOR_ACID_GREEN, int(190 * overall_alpha)), 1
        )
        dot_pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(dot_pen)
        painter.drawLine(QPointF(local_start), current_head)

        for _ in range(rng.randint(6, 14)):
            t = rng.random()
            bx = (
                local_start.x()
                + (curr_target_x - local_start.x()) * t
                + perp_x * rng.uniform(-16, 16)
            )
            by = (
                local_start.y()
                + (curr_target_y - local_start.y()) * t
                + perp_y * rng.uniform(-16, 16)
            )
            bw = snap_pixel(
                rng.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 4))
            )
            bh = snap_pixel(rng.choice((PIXEL_SIZE, PIXEL_SIZE * 2)))
            bcolor = pick_palette_color()
            painter.fillRect(
                int(bx - bw / 2),
                int(by - bh / 2),
                bw,
                bh,
                with_alpha(
                    bcolor, int(rng.randint(140, 240) * overall_alpha)
                ),
            )

        for _ in range(rng.randint(2, 5)):
            t = rng.random()
            lx = local_start.x() + (curr_target_x - local_start.x()) * t
            ly = local_start.y() + (curr_target_y - local_start.y()) * t
            bar_w = rng.randint(20, 80)
            bar_h = rng.choice((1, 2, 3))
            painter.fillRect(
                int(lx - bar_w / 2),
                int(ly - bar_h / 2),
                bar_w,
                bar_h,
                with_alpha(
                    rng.choice(
                        (COLOR_CRIMSON, COLOR_ACID_GREEN, COLOR_WHITE)
                    ),
                    int(180 * overall_alpha),
                ),
            )

        pulse = (now * 2.2) % 1.0
        if self._build_progress >= 0.15:
            p_dist = draw_dist * pulse
            px = (
                local_start.x() + (dx / total_dist) * p_dist
                if total_dist > 0
                else local_start.x()
            )
            py = (
                local_start.y() + (dy / total_dist) * p_dist
                if total_dist > 0
                else local_start.y()
            )
            pulse_size = 8
            painter.fillRect(
                int(px - pulse_size / 2),
                int(py - pulse_size / 2),
                pulse_size,
                pulse_size,
                with_alpha(COLOR_ACID_GREEN, int(255 * overall_alpha)),
            )
            painter.fillRect(
                int(px - pulse_size / 2 - 3),
                int(py - pulse_size / 2 - 2),
                pulse_size,
                pulse_size,
                with_alpha(COLOR_CRIMSON, int(160 * overall_alpha)),
            )

        anchor_size = 14
        anchor_rect = QRect(
            local_start.x() - anchor_size // 2,
            local_start.y() - anchor_size // 2,
            anchor_size,
            anchor_size,
        )
        painter.setPen(
            QPen(with_alpha(COLOR_ACID_GREEN, int(230 * overall_alpha)), 1)
        )
        painter.drawRect(anchor_rect)
        painter.drawLine(
            local_start.x() - 10,
            local_start.y(),
            local_start.x() + 10,
            local_start.y(),
        )
        painter.drawLine(
            local_start.x(),
            local_start.y() - 10,
            local_start.x(),
            local_start.y() + 10,
        )

        if self._build_progress >= 0.35:
            reticle_progress = (
                min(1.0, (self._build_progress - 0.35) / 0.65)
                * overall_alpha
            )
            reticle_size = 60
            jitter_head_x = current_head.x() + (
                rng.uniform(-3, 3) if rng.random() < 0.6 else 0
            )
            jitter_head_y = current_head.y() + (
                rng.uniform(-3, 3) if rng.random() < 0.6 else 0
            )

            reticle_rect = QRect(
                int(jitter_head_x - reticle_size // 2),
                int(jitter_head_y - reticle_size // 2),
                reticle_size,
                reticle_size,
            )
            elapsed = now - self._start_time
            rotation = elapsed * math.tau * 0.9

            CyberKiroshiReticle.draw(
                painter,
                reticle_rect,
                progress=reticle_progress,
                color=COLOR_CRIMSON,
                bracket_offset=int(abs(math.sin(elapsed * 6.0)) * 6),
                rotation=rotation,
                label="POINTER // GLITCH",
                locked=True,
            )

            if rng.random() < 0.7:
                draw_glitch_mass(
                    painter,
                    QPoint(int(jitter_head_x), int(jitter_head_y)),
                    base_size=24,
                    intensity=0.8 * overall_alpha,
                    seed=self._frame,
                )

            font = get_hud_font(10, bold=True)
            painter.setFont(font)
            dist_int = int(total_dist)
            glitch_tag = (
                f"TARGET: [{self._target_pos.x():04d},{self._target_pos.y():04d}] // DIST:{dist_int:04d}px"
                if rng.random() < 0.8
                else f"ERR//0x{rng.randint(0x1000, 0xFFFF):04X} // SYNC_ERR:{dist_int:04d}"
            )
            tag_rect = QRect(
                int(jitter_head_x + 36), int(jitter_head_y - 8), 260, 16
            )
            painter.fillRect(
                tag_rect,
                with_alpha(COLOR_OBSIDIAN, int(220 * overall_alpha)),
            )
            painter.setPen(
                QPen(
                    with_alpha(COLOR_CRIMSON, int(255 * overall_alpha)), 1
                )
            )
            painter.drawRect(tag_rect)
            painter.setPen(
                with_alpha(COLOR_WHITE, int(240 * overall_alpha))
            )
            painter.drawText(
                tag_rect.adjusted(4, 0, 0, 0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                glitch_tag,
            )

        painter.end()
