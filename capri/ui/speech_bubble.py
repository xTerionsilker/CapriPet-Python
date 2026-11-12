"""CyberHudBubble presentation widget for CapriPet speech system."""

from __future__ import annotations

import random
import time
from collections.abc import Callable

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget

from .theme import (
    ACID_GREEN,
    ELECTRIC_BLUE,
    NEON_CRIMSON,
    PURE_WHITE,
    get_hud_font,
)

_CHEVRONS = {
    "left": "◀",
    "right": "▶",
    "down": "▼",
    "up": "▲",
    "none": "",
}


class CyberHudBubble(QWidget):
    """Киберпанк-контейнер реплики со скошенными углами и анимацией развертывания."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        title: str = "[CAPRI://NET_LINK]",
        chamfer: int = 16,
        shadow_offset: int = 6,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._chamfer = chamfer
        self._shadow_offset = shadow_offset
        self._pointer_direction = "left"
        self._is_excited: bool = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._anim_phase: str = "opening"
        self._anim_progress: float = 0.0
        self._anim_duration: float = 0.25
        self._anim_start_time: float = 0.0
        self._anim_callback: Callable[[], None] | None = None

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._on_anim_tick)

    @property
    def anim_phase(self) -> str:
        return self._anim_phase

    @anim_phase.setter
    def anim_phase(self, value: str) -> None:
        self._anim_phase = value

    def set_title(self, title: str) -> None:
        if self._title != title:
            self._title = title
            self.update()

    def set_pointer_direction(self, direction: str) -> None:
        if self._pointer_direction != direction:
            self._pointer_direction = direction
            self.update()

    def set_excited(self, excited: bool) -> None:
        if self._is_excited != excited:
            self._is_excited = excited
            self.update()

    def start_open(
        self,
        duration_ms: int = 250,
        callback: Callable[[], None] | None = None,
    ) -> None:
        self._anim_phase = "opening"
        self._anim_progress = 0.0
        self._anim_duration = max(0.06, duration_ms / 1000.0)
        self._anim_start_time = time.monotonic()
        self._anim_callback = callback
        self._anim_timer.start()
        self.update()

    def start_close(
        self,
        duration_ms: int = 220,
        callback: Callable[[], None] | None = None,
    ) -> None:
        self._anim_phase = "closing"
        self._anim_progress = 0.0
        self._anim_duration = max(0.05, duration_ms / 1000.0)
        self._anim_start_time = time.monotonic()
        self._anim_callback = callback
        self._anim_timer.start()
        self.update()

    def stop_animations(self) -> None:
        self._anim_timer.stop()
        self._anim_callback = None
        self.update()

    def stop_glitch(self) -> None:
        self.stop_animations()

    def _on_anim_tick(self) -> None:
        elapsed = time.monotonic() - self._anim_start_time
        progress = min(1.0, elapsed / self._anim_duration)
        self._anim_progress = progress

        parent_w = self.parentWidget()
        if parent_w is not None and hasattr(
            parent_w, "update_anim_opacity"
        ):
            parent_w.update_anim_opacity(self._anim_phase, progress)

        self.update()

        if progress >= 1.0:
            self._anim_timer.stop()
            cb = self._anim_callback
            self._anim_callback = None
            if self._anim_phase == "opening":
                self._anim_phase = "idle"
            elif self._anim_phase == "closing":
                self._anim_phase = "closed"
            if cb is not None:
                cb()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = self.width()
        h = self.height()
        c = self._chamfer
        so = self._shadow_offset

        bw = max(1, w - so)
        bh = max(1, h - so)

        y_mid = bh // 2
        x_mid = bw // 2
        y_top = 0
        y_bot = 0

        phase = self._anim_phase
        prog = self._anim_progress

        if phase == "opening":
            if prog < 0.22:
                p1 = prog / 0.22
                w_beam = max(14, int(bw * (1.0 - (1.0 - p1) ** 2)))
                x_start = (bw - w_beam) // 2

                painter.fillRect(
                    x_start - 6,
                    y_mid - 4,
                    w_beam + 12,
                    8,
                    QColor(246, 2, 63, int(190 * p1)),
                )

                painter.fillRect(
                    x_start,
                    y_mid - 2,
                    w_beam,
                    4,
                    QColor(18, 110, 233, 240),
                )

                core_w = max(1, w_beam - 8)
                painter.fillRect(
                    x_start + 4,
                    y_mid - 1,
                    core_w,
                    2,
                    QColor(249, 249, 249, 255),
                )

                painter.fillRect(
                    x_start - 4,
                    y_mid - 3,
                    3,
                    6,
                    QColor(246, 2, 63, 220),
                )
                painter.fillRect(
                    x_start + w_beam + 1,
                    y_mid - 3,
                    3,
                    6,
                    QColor(18, 110, 233, 220),
                )
                return

            p2 = (prog - 0.22) / 0.78
            e_h = 1.0 - (1.0 - p2) ** 3
            h_cur = max(6, int(bh * e_h))
            y_top = max(0, y_mid - h_cur // 2)
            y_bot = y_top + h_cur

            painter.setClipRect(QRect(-12, y_top, w + 24, h_cur + so + 12))
            intensity = (1.0 - p2) * 0.7

        elif phase == "closing":
            if prog < 0.25:
                intensity = 1.0
            elif prog < 0.75:
                p_c = (prog - 0.25) / 0.50
                e_c = p_c**2
                h_cur = max(4, int(bh * (1.0 - e_c)))
                y_top = y_mid - h_cur // 2
                y_bot = y_top + h_cur

                painter.setClipRect(
                    QRect(-12, y_top, w + 24, h_cur + so + 12)
                )
                intensity = 0.8
            else:
                p_h = (prog - 0.75) / 0.25
                w_beam = max(2, int(bw * (1.0 - p_h**2)))
                x_start = (bw - w_beam) // 2
                alpha = int(255 * (1.0 - p_h))

                painter.fillRect(
                    x_start - 4,
                    y_mid - 3,
                    w_beam + 8,
                    6,
                    QColor(246, 2, 63, int(alpha * 0.5)),
                )
                painter.fillRect(
                    x_start,
                    y_mid - 1,
                    w_beam,
                    3,
                    QColor(18, 110, 233, alpha),
                )
                painter.fillRect(
                    x_mid - 2,
                    y_mid - 2,
                    4,
                    4,
                    QColor(249, 249, 249, alpha),
                )
                return
        else:
            intensity = 0.0

        is_glitch = intensity > 0.05
        shake_x = (
            int(random.uniform(-4, 4) * intensity) if is_glitch else 0
        )
        shake_y = 0
        if self._is_excited:
            shake_x += random.randint(-2, 2)
            shake_y = random.randint(-1, 1)

        dir_ = self._pointer_direction
        path = QPainterPath()
        path.moveTo(shake_x, shake_y)

        if dir_ == "up":
            path.lineTo(x_mid - 12 + shake_x, shake_y)
            path.lineTo(x_mid - 5 + shake_x, 6 + shake_y)
            path.lineTo(x_mid + 5 + shake_x, 6 + shake_y)
            path.lineTo(x_mid + 12 + shake_x, shake_y)
        path.lineTo(bw - c + shake_x, shake_y)

        path.lineTo(bw + shake_x, c + shake_y)

        if dir_ == "right":
            path.lineTo(bw + shake_x, y_mid - 12 + shake_y)
            path.lineTo(bw + shake_x - 6, y_mid - 5 + shake_y)
            path.lineTo(bw + shake_x - 6, y_mid + 5 + shake_y)
            path.lineTo(bw + shake_x, y_mid + 12 + shake_y)
        path.lineTo(bw + shake_x, bh + shake_y)

        if dir_ == "down":
            path.lineTo(x_mid + 12 + shake_x, bh + shake_y)
            path.lineTo(x_mid + 5 + shake_x, bh - 6 + shake_y)
            path.lineTo(x_mid - 5 + shake_x, bh - 6 + shake_y)
            path.lineTo(x_mid - 12 + shake_x, bh + shake_y)
        path.lineTo(c + shake_x, bh + shake_y)
        path.lineTo(shake_x, bh - c + shake_y)

        if dir_ == "left":
            path.lineTo(shake_x, y_mid + 12 + shake_y)
            path.lineTo(shake_x + 6, y_mid + 5 + shake_y)
            path.lineTo(shake_x + 6, y_mid - 5 + shake_y)
            path.lineTo(shake_x, y_mid - 12 + shake_y)
        path.closeSubpath()

        shadow_path = path.translated(so, so)
        shadow_alpha = int(90 + 50 * intensity) if is_glitch else 90
        painter.fillPath(shadow_path, QColor(246, 2, 63, shadow_alpha))

        painter.fillPath(path, QColor(2, 1, 6, 248))

        painter.save()
        painter.setClipPath(path)
        scanline_alpha = (
            int(random.randint(15, 45) * intensity) if is_glitch else 14
        )
        scanline_pen = QPen(QColor(246, 2, 63, max(8, scanline_alpha)), 1)
        painter.setPen(scanline_pen)
        for y in range(0, bh, 3):
            painter.drawLine(shake_x - 10, y, bw + shake_x + 10, y)

        if phase in ("opening", "closing") or is_glitch:
            sweep_y = int(bh * ((time.monotonic() * 2.5) % 1.0))
            painter.fillRect(
                shake_x - 10, sweep_y, bw + 20, 2, QColor(246, 2, 63, 110)
            )

        painter.restore()

        if is_glitch and intensity > 0.08:
            dx = int(random.uniform(2, 6) * intensity)
            red_path = path.translated(-dx, 0)
            painter.strokePath(
                red_path, QPen(QColor(246, 2, 63, int(160 * intensity)), 2)
            )
            green_shift = path.translated(dx, 0)
            painter.strokePath(
                green_shift,
                QPen(QColor(6, 248, 104, int(160 * intensity)), 2),
            )

        crimson_pen = QPen(QColor(NEON_CRIMSON), 2)
        painter.strokePath(path, crimson_pen)

        accent_pen = QPen(QColor(ACID_GREEN), 2)
        painter.setPen(accent_pen)

        painter.drawLine(bw - c + shake_x, shake_y, bw + shake_x, c + shake_y)
        painter.drawLine(c + shake_x, bh + shake_y, shake_x, bh - c + shake_y)

        painter.drawLine(shake_x, shake_y, shake_x + 10, shake_y)
        painter.drawLine(shake_x, shake_y, shake_x, 10 + shake_y)
        painter.drawLine(shake_x, bh - 10 + shake_y, shake_x, bh + shake_y)
        painter.drawLine(shake_x, bh + shake_y, shake_x + 10, bh + shake_y)
        painter.drawLine(bw - 10 + shake_x, bh + shake_y, bw + shake_x, bh + shake_y)
        painter.drawLine(bw + shake_x, bh - 10 + shake_y, bw + shake_x, bh + shake_y)

        if self._is_excited:
            spark_pen = QPen(QColor(PURE_WHITE), 1.5)
            painter.setPen(spark_pen)
            painter.drawLine(bw + shake_x, c + shake_y, bw + shake_x + 6, c - 6 + shake_y)
            painter.drawLine(bw + shake_x - 2, c - 2 + shake_y, bw + shake_x + 4, c - 7 + shake_y)
            painter.setPen(QPen(QColor(ACID_GREEN), 1.5))
            painter.drawLine(shake_x, bh - c + shake_y, shake_x - 6, bh - c + 6 + shake_y)
            painter.drawLine(shake_x - 2, bh - c + 2 + shake_y, shake_x - 6, bh - c + 8 + shake_y)

        chevron_color = (
            QColor(NEON_CRIMSON) if is_glitch else QColor(ACID_GREEN)
        )
        painter.setPen(QPen(chevron_color, 2))
        if dir_ == "left":
            painter.drawLine(shake_x + 3, y_mid, shake_x + 1, y_mid)
        elif dir_ == "right":
            painter.drawLine(
                bw + shake_x - 3, y_mid, bw + shake_x - 1, y_mid
            )
        elif dir_ == "down":
            painter.drawLine(
                x_mid + shake_x, bh - 3, x_mid + shake_x, bh - 1
            )
        elif dir_ == "up":
            painter.drawLine(x_mid + shake_x, 3, x_mid + shake_x, 1)

        if is_glitch and intensity > 0.15:
            for _ in range(random.randint(2, 4)):
                sy = random.randint(0, bh - 1)
                sh = random.randint(1, 3)
                sw = random.randint(bw // 4, max(bw // 4 + 1, bw))
                sx = random.randint(0, max(0, bw - sw))
                slice_color = QColor(
                    random.choice(
                        (
                            NEON_CRIMSON,
                            ACID_GREEN,
                            PURE_WHITE,
                            ELECTRIC_BLUE,
                        )
                    )
                )
                slice_color.setAlpha(
                    int(random.randint(40, 100) * intensity)
                )
                painter.fillRect(sx, sy, sw, sh, slice_color)

        font = get_hud_font(11, bold=True)
        painter.setFont(font)

        badge_w = min(190, max(120, bw - c - 24))
        badge_rect = QRect(16 + shake_x, 5 + shake_y, badge_w, 16)
        painter.fillRect(
            QRect(12 + shake_x, 5 + shake_y, badge_w + 6, 16),
            QColor(246, 2, 63, 40),
        )
        painter.fillRect(
            QRect(12 + shake_x, 5 + shake_y, 2, 16),
            QColor(ACID_GREEN),
        )

        t_phase = int(time.monotonic() * 4) % 4
        glyph = ("◈", "◇", "◆", "◈")[t_phase]
        chevron = _CHEVRONS.get(dir_, "")
        title_with_dir = f"{glyph} {self._title} {chevron}".strip()

        painter.setPen(QColor(ACID_GREEN))
        painter.drawText(
            badge_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            title_with_dir,
        )

        if phase == "opening" and 0.22 <= prog < 0.95:
            painter.fillRect(0, y_top - 1, bw, 2, QColor(246, 2, 63, 230))
            painter.fillRect(0, y_bot - 1, bw, 2, QColor(6, 248, 104, 230))
        elif phase == "closing" and 0.25 <= prog < 0.75:
            painter.fillRect(0, y_top - 1, bw, 3, QColor(246, 2, 63, 245))
            painter.fillRect(0, y_bot - 1, bw, 3, QColor(6, 248, 104, 245))
