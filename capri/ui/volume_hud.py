"""Cyber Audio HUD оверлей системной мастер-громкости в палитре Studio Trigger."""

from __future__ import annotations

import contextlib
import logging

from PySide6.QtCore import QPropertyAnimation, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

from .theme import (
    CHAMFER_HUD,
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_WHITE,
    get_hud_font,
    get_terminal_font,
)

logger = logging.getLogger(__name__)
HUD_WIDTH = 340
HUD_HEIGHT = 68


class CyberVolumeHud(QWidget):
    """Автономный экранный OSD-оверлей системной громкости со скошенными углами."""

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

        self._volume_percent: int = 50
        self._is_muted: bool = False
        self._volume_db: float = 0.0

        self.setFixedSize(HUD_WIDTH, HUD_HEIGHT)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(240)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_fade_out)

    def _reposition(self) -> None:
        """Центрировать HUD в верхней четверти активного экрана."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.left() + (geo.width() - HUD_WIDTH) // 2
        y = geo.top() + int(geo.height() * 0.08)
        self.move(x, y)

    def show_volume(
        self, volume_percent: int, is_muted: bool = False, volume_db: float = 0.0
    ) -> None:
        """Отобразить оверлей с актуальным уровнем громкости и сбросить таймер скрытия."""
        self._volume_percent = max(0, min(100, int(volume_percent)))
        self._is_muted = bool(is_muted)
        self._volume_db = float(volume_db)

        self._reposition()
        self.show()
        self.raise_()
        self.update()

        self._fade_anim.stop()
        self._opacity_effect.setOpacity(1.0)
        self._hide_timer.start(1800)

    def _start_fade_out(self) -> None:
        """Запустить плавное исчезновение оверлея."""
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_finished)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        with contextlib.suppress(Exception):
            self._fade_anim.finished.disconnect(self._on_fade_finished)
        if self._opacity_effect.opacity() <= 0.05:
            self.hide()

    def _create_chamfered_path(self, rect: QRectF, c: float) -> QPainterPath:
        """Полигон со скошенными под 45 градусов углами в стиле Studio Trigger."""
        path = QPainterPath()
        l, t, r, b = rect.left(), rect.top(), rect.right(), rect.bottom()
        path.moveTo(l + c, t)
        path.lineTo(r - c, t)
        path.lineTo(r, t + c)
        path.lineTo(r, b - c)
        path.lineTo(r - c, b)
        path.lineTo(l + c, b)
        path.lineTo(l, b - c)
        path.lineTo(l, t + c)
        path.closeSubpath()
        return path

    def paintEvent(self, event) -> None:
        """Отрисовка кибернетического интерфейса шкалы звука."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        c = float(CHAMFER_HUD)

        bg_path = self._create_chamfered_path(rect, c)
        painter.fillPath(bg_path, QColor(2, 1, 6, 235))

        border_color = COLOR_CRIMSON if (self._is_muted or self._volume_percent >= 85) else COLOR_ACID_GREEN
        pen = QPen(border_color, 1.5)
        painter.strokePath(bg_path, pen)

        self._draw_header(painter, rect)
        self._draw_progress_bar(painter, rect, border_color)
        painter.end()

    def _draw_header(self, painter: QPainter, rect: QRectF) -> None:
        """Отрисовка заголовка и телеметрии децибел."""
        painter.setFont(get_hud_font(9, bold=True))
        painter.setPen(COLOR_ACID_GREEN)
        header_text = "// MASTER AUDIO BUS // [SYS.CORE]"
        painter.drawText(int(rect.left() + 14), int(rect.top() + 18), header_text)

        painter.setFont(get_hud_font(9, bold=True))
        if self._is_muted:
            painter.setPen(COLOR_CRIMSON)
            right_text = "[MUTED // BLACKWALL SILENCE]"
        else:
            painter.setPen(COLOR_WHITE)
            right_text = f"{self._volume_db:+.1f} dB"
        painter.drawText(
            QRect(int(rect.left()), int(rect.top() + 6), int(rect.width() - 14), 16),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            right_text,
        )

    def _draw_progress_bar(self, painter: QPainter, rect: QRectF, active_color: QColor) -> None:
        """Отрисовка сегментированной шкалы громкости."""
        bar_x = rect.left() + 14
        bar_y = rect.top() + 28
        bar_w = rect.width() - 84
        bar_h = 16

        painter.fillRect(QRectF(bar_x, bar_y, bar_w, bar_h), QColor(10, 8, 18, 180))

        num_segments = 25
        filled_segments = round((self._volume_percent / 100.0) * num_segments)
        seg_gap = 2.0
        seg_w = (bar_w - (num_segments - 1) * seg_gap) / num_segments

        for i in range(num_segments):
            seg_rect = QRectF(bar_x + i * (seg_w + seg_gap), bar_y + 2, seg_w, bar_h - 4)
            if not self._is_muted and i < filled_segments:
                seg_color = COLOR_CRIMSON if i >= int(num_segments * 0.85) else COLOR_ACID_GREEN
                painter.fillRect(seg_rect, seg_color)
            else:
                painter.fillRect(seg_rect, QColor(25, 20, 35, 120))

        painter.setFont(get_terminal_font(12, bold=True))
        painter.setPen(COLOR_WHITE if not self._is_muted else COLOR_CRIMSON)
        pct_text = "MUTE" if self._is_muted else f"{self._volume_percent}%"
        painter.drawText(
            QRect(int(bar_x + bar_w + 10), int(bar_y), 56, int(bar_h)),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            pct_text,
        )
