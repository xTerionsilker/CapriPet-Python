from __future__ import annotations

import time

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .fonts import get_hud_font
from .theme import (
    ACID_GREEN,
    ELECTRIC_BLUE,
    NEON_CRIMSON,
    OBSIDIAN_BLACK,
    PIXEL_FONT,
    PURE_WHITE,
)

_CORNER_CUT = 8
_TASKBAR_MARGIN = 12


class CyberVoiceHud(QWidget):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setWindowTitle("Capri Voice HUD")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._status_text = "LISTENING"
        self._recognized_text = ""
        self._target_recognized_text = ""
        self._revealed_chars = 0
        self._mode_tag = "CAPRI//VOICE_INPUT"
        self._anim_tick = 0
        self._hide_timestamp = 0.0


        self._width = 460
        self._height = 76
        self.setFixedSize(self._width, self._height)


        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(45)
        self._anim_timer.timeout.connect(self._on_anim_tick)


        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self._check_auto_hide)

    def show_hud(self, status: str, mode: str = "AWAITING_INPUT") -> None:
        self._status_text = status.upper()
        self._mode_tag = f"CAPRI//{mode.upper()}"
        self._auto_hide_timer.stop()
        self._reposition()
        if not self.isVisible():
            self.show()
            self._anim_timer.start()
        self.update()

    def set_recognized_text(self, text: str, keep_ms: int = 2500) -> None:
        clean = text.strip()
        self._target_recognized_text = clean
        self._revealed_chars = 0
        self._status_text = "RECOGNIZED"
        self._hide_timestamp = time.monotonic() + (keep_ms / 1000.0)
        self._auto_hide_timer.stop()
        self._auto_hide_timer.start(keep_ms)
        self._reposition()
        if not self.isVisible():
            self.show()
            self._anim_timer.start()
        self.update()

    def hide_hud(self, delay_ms: int = 0) -> None:
        if delay_ms <= 0:
            self._auto_hide_timer.stop()
            self._anim_timer.stop()
            self.hide()
            self._target_recognized_text = ""
            self._recognized_text = ""
            self._revealed_chars = 0
        else:
            self._auto_hide_timer.stop()
            self._auto_hide_timer.start(delay_ms)

    def _check_auto_hide(self) -> None:
        self.hide_hud(0)

    def _reposition(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            screens = QGuiApplication.screens()
            if screens:
                screen = screens[0]
            else:
                return

        full_geo = screen.geometry()
        avail_geo = screen.availableGeometry()


        x = avail_geo.left() + (avail_geo.width() - self.width()) // 2


        if avail_geo.bottom() < full_geo.bottom() - 4:
            y = avail_geo.bottom() - self.height() - _TASKBAR_MARGIN
        elif avail_geo.top() > full_geo.top() + 4:
            y = avail_geo.bottom() - self.height() - _TASKBAR_MARGIN
        elif avail_geo.left() > full_geo.left() + 4:
            y = avail_geo.bottom() - self.height() - _TASKBAR_MARGIN
        elif avail_geo.right() < full_geo.right() - 4:
            y = avail_geo.bottom() - self.height() - _TASKBAR_MARGIN
        else:

            y = full_geo.bottom() - self.height() - (_TASKBAR_MARGIN + 36)


        y = max(avail_geo.top() + 5, min(y, full_geo.bottom() - self.height() - 4))
        self.move(x, y)

    def _on_anim_tick(self) -> None:
        self._anim_tick += 1
        if len(self._recognized_text) < len(self._target_recognized_text):
            step = max(1, (len(self._target_recognized_text) - len(self._recognized_text)) // 3 + 1)
            self._revealed_chars += step
            self._recognized_text = self._target_recognized_text[: self._revealed_chars]
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        rect = self.rect().adjusted(0, 0, -1, -1)


        painter.fillRect(rect, QColor(OBSIDIAN_BLACK))


        scan_pen = QPen(QColor(242, 13, 46, 18), 1)
        painter.setPen(scan_pen)
        for y in range(rect.top() + 2, rect.bottom(), 3):
            painter.drawLine(rect.left() + 2, y, rect.right() - 2, y)


        cut = _CORNER_CUT
        border_pen = QPen(QColor(NEON_CRIMSON), 1)
        painter.setPen(border_pen)


        painter.drawLine(rect.left() + cut, rect.top(), rect.right(), rect.top())

        painter.drawLine(rect.right(), rect.top(), rect.right(), rect.bottom() - cut)

        painter.drawLine(rect.right(), rect.bottom() - cut, rect.right() - cut, rect.bottom())

        painter.drawLine(rect.right() - cut, rect.bottom(), rect.left(), rect.bottom())

        painter.drawLine(rect.left(), rect.bottom(), rect.left(), rect.top() + cut)

        painter.drawLine(rect.left(), rect.top() + cut, rect.left() + cut, rect.top())


        painter.fillRect(QRect(rect.left() + cut + 6, rect.top() + 3, 4, 3), QColor(ACID_GREEN))
        painter.fillRect(QRect(rect.left() + cut + 12, rect.top() + 3, 8, 3), QColor(PURE_WHITE))


        painter.setPen(QPen(QColor(ACID_GREEN), 2))
        painter.drawLine(rect.left() + 2, rect.top() + cut + 4, rect.left() + 2, rect.bottom() - 6)


        painter.setPen(QPen(QColor(ELECTRIC_BLUE), 2))
        painter.drawLine(rect.right() - 2, rect.top() + 6, rect.right() - 2, rect.bottom() - cut - 4)


        eq_x = rect.right() - 95
        eq_y_base = rect.top() + 18
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(8):
            bar_height = ((self._anim_tick + i * 3) % 7) * 2 + 3
            bar_color = QColor(ACID_GREEN) if i < 6 else QColor(NEON_CRIMSON)
            painter.fillRect(QRect(eq_x + i * 5, eq_y_base - bar_height + 12, 3, bar_height), bar_color)


        rec_dot_color = QColor(NEON_CRIMSON) if (self._anim_tick // 6) % 2 == 0 else QColor(11, 11, 11)
        painter.fillRect(QRect(eq_x + 52, rect.top() + 10, 6, 6), rec_dot_color)


        font_header = get_hud_font(12, bold=True)
        painter.setFont(font_header)
        painter.setPen(QColor(ACID_GREEN))

        status_display = f"▶ {self._mode_tag} // [{self._status_text}]"
        painter.drawText(rect.left() + cut + 20, rect.top() + 18, status_display)


        font_sub = get_hud_font(10, bold=False)
        painter.setFont(font_sub)
        painter.setPen(QColor(ELECTRIC_BLUE))
        painter.drawText(rect.right() - 95, rect.top() + 14, "MIC//IN")


        painter.setPen(QPen(QColor(NEON_CRIMSON), 1))
        painter.drawLine(rect.left() + cut + 4, rect.top() + 24, rect.right() - 8, rect.top() + 24)


        font_text = get_hud_font(13, bold=True)
        painter.setFont(font_text)

        display_text = self._recognized_text
        if not display_text:
            dots = "." * ((self._anim_tick // 8) % 4)
            display_text = f"Слушаю{dots}"
            painter.setPen(QColor(PURE_WHITE))
        else:
            painter.setPen(QColor(PURE_WHITE))


        text_rect = QRect(rect.left() + cut + 14, rect.top() + 30, rect.width() - cut - 30, 36)

        cursor_char = "█" if (self._anim_tick // 7) % 2 == 0 else ""
        text_with_cursor = f"«{display_text}»{cursor_char}" if self._recognized_text else f"{display_text}{cursor_char}"
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            text_with_cursor,
        )

        painter.end()
