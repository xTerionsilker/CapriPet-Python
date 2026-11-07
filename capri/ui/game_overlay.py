from __future__ import annotations

import random
import time
from typing import Callable, Optional

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget

from .theme import (
    ACID_GREEN,
    NEON_CRIMSON,
    OBSIDIAN_BLACK,
    PURE_WHITE,
    get_hud_font,
)


class SilentPresenceGlyph(QWidget):
    anim_finished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._pulse_alpha = 140
        self._pulse_dir = 1
        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._on_pulse)

        self._anim_phase: str = "idle"
        self._anim_progress: float = 1.0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(25)
        self._anim_timer.timeout.connect(self._on_anim_step)
        self._anim_start_time: float = 0.0
        self._anim_duration_ms: float = 250.0
        self._on_anim_done: Optional[Callable[[], None]] = None

        self.setFixedSize(140, 36)
        self._reposition()
    def _reposition(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geo = screen.geometry()
        margin = 16
        x = geo.right() - self.width() - margin
        y = geo.top() + margin
        self.move(x, y)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._reposition()
        if not self._timer.isActive():
            self._timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()
        self._anim_timer.stop()

    def _on_pulse(self) -> None:
        self._pulse_alpha += self._pulse_dir * 3
        if self._pulse_alpha >= 210:
            self._pulse_alpha = 210
            self._pulse_dir = -1
        elif self._pulse_alpha <= 90:
            self._pulse_alpha = 90
            self._pulse_dir = 1
        self.update()

    def start_materialize(
        self, duration_ms: int = 250, callback: Optional[Callable[[], None]] = None
    ) -> None:
        self._reposition()
        self.show()
        self._anim_phase = "materializing"
        self._anim_duration_ms = max(50.0, float(duration_ms))
        self._anim_start_time = time.monotonic()
        self._anim_progress = 0.0
        self._on_anim_done = callback
        self._anim_timer.start()
        self.update()

    def start_dissolve(
        self, duration_ms: int = 220, callback: Optional[Callable[[], None]] = None
    ) -> None:
        self._anim_phase = "dissolving"
        self._anim_duration_ms = max(50.0, float(duration_ms))
        self._anim_start_time = time.monotonic()
        self._anim_progress = 0.0
        self._on_anim_done = callback
        self._anim_timer.start()
        self.update()
    def _on_anim_step(self) -> None:
        elapsed = (time.monotonic() - self._anim_start_time) * 1000.0
        p = min(1.0, elapsed / self._anim_duration_ms)
        self._anim_progress = p
        self.update()
        if p >= 1.0:
            self._anim_timer.stop()
            callback = self._on_anim_done
            self._on_anim_done = None
            if self._anim_phase == "dissolving":
                self._anim_phase = "idle"
                self.hide()
            else:
                self._anim_phase = "idle"
            self.anim_finished.emit()
            if callback:
                callback()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cut = 8

        phase = self._anim_phase
        prog = self._anim_progress

        if phase == "materializing":
            wire_alpha = int(255 * min(1.0, prog * 1.6))
            fill_alpha = int(170 * max(0.0, (prog - 0.4) / 0.6))
            content_alpha = int(255 * max(0.0, (prog - 0.5) / 0.5))
        elif phase == "dissolving":
            wire_alpha = int(255 * (1.0 - prog))
            fill_alpha = int(170 * max(0.0, 1.0 - prog * 2.0))
            content_alpha = int(255 * max(0.0, 1.0 - prog * 2.2))
        else:
            wire_alpha = 255
            fill_alpha = 170
            content_alpha = 255

        path = QPainterPath()
        path.moveTo(cut, 0)
        path.lineTo(w, 0)
        path.lineTo(w, h - cut)
        path.lineTo(w - cut, h)
        path.lineTo(0, h)
        path.lineTo(0, cut)
        path.closeSubpath()
        if fill_alpha > 0:
            bg_color = QColor(OBSIDIAN_BLACK)
            bg_color.setAlpha(fill_alpha)
            painter.fillPath(path, bg_color)

        if wire_alpha > 0:
            pen = QPen(QColor(NEON_CRIMSON), 1.2)
            c = pen.color()
            c.setAlpha(wire_alpha)
            pen.setColor(c)
            painter.setPen(pen)
            painter.drawPath(path)

            bracket_pen = QPen(QColor(ACID_GREEN), 1.4)
            bc = bracket_pen.color()
            bc.setAlpha(wire_alpha)
            bracket_pen.setColor(bc)
            painter.setPen(bracket_pen)
            painter.drawLine(0, cut, cut, 0)
            painter.drawLine(w - cut, h, w, h - cut)

        if content_alpha > 0:
            dot_color = QColor(ACID_GREEN)
            dot_color.setAlpha(int(self._pulse_alpha * (content_alpha / 255.0)))
            painter.setBrush(dot_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(12, h // 2 - 4, 8, 8)

            text_color = QColor(PURE_WHITE)
            text_color.setAlpha(content_alpha)
            painter.setPen(QPen(text_color))
            painter.setFont(get_hud_font(pixel_size=10, bold=True))
            text_rect = QRect(26, 0, w - 30, h)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                "CAPRI // STEALTH",
            )
