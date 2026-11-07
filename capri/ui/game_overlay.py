"""Компактный индикатор присутствия питомца поверх полноэкранных приложений.

Отображает минималистичный пульсирующий HUD-глиф в игровом режиме,
не перехватывая ввод пользователя.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import (
    QColor,
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
    """Пульсирующий ненавязчивый индикатор присутствия в углу экрана."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating, True
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        self._pulse_alpha = 140
        self._pulse_dir = 1
        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._on_pulse)

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

    def _on_pulse(self) -> None:
        self._pulse_alpha += self._pulse_dir * 3
        if self._pulse_alpha >= 210:
            self._pulse_alpha = 210
            self._pulse_dir = -1
        elif self._pulse_alpha <= 90:
            self._pulse_alpha = 90
            self._pulse_dir = 1
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cut = 8

        path = QPainterPath()
        path.moveTo(cut, 0)
        path.lineTo(w, 0)
        path.lineTo(w, h - cut)
        path.lineTo(w - cut, h)
        path.lineTo(0, h)
        path.lineTo(0, cut)
        path.closeSubpath()
        bg_color = QColor(OBSIDIAN_BLACK)
        bg_color.setAlpha(170)
        painter.fillPath(path, bg_color)

        pen = QPen(QColor(NEON_CRIMSON), 1.2)
        painter.setPen(pen)
        painter.drawPath(path)

        bracket_pen = QPen(QColor(ACID_GREEN), 1.4)
        painter.setPen(bracket_pen)
        painter.drawLine(0, cut, cut, 0)
        painter.drawLine(w - cut, h, w, h - cut)

        dot_color = QColor(ACID_GREEN)
        dot_color.setAlpha(self._pulse_alpha)
        painter.setBrush(dot_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(12, h // 2 - 4, 8, 8)

        text_pen = QPen(QColor(PURE_WHITE))
        painter.setPen(text_pen)
        painter.setFont(get_hud_font(pixel_size=10, bold=True))
        text_rect = QRect(26, 0, w - 30, h)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "CAPRI // STEALTH",
        )
