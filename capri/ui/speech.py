from __future__ import annotations

from html import escape

from PySide6.QtCore import QElapsedTimer, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
    QScreen,
)
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .placement import GAP, pick_position, pick_side_position
from .speech_sfx import get_speech_sfx

_TEXT_COLOR = "#00f0ff"
_TEXT_WIDTH = 420

_STYLE = """
QLabel#text {
    background: transparent;
    color: #00f0ff;
    font-family: "Press Start 2P", "Pixelify Sans", "VT323", "Terminus",
        "JetBrains Mono", "DejaVu Sans Mono", monospace;
    font-size: 13px;
    letter-spacing: 1px;
}
"""

_active_windows: set["SpeechWindow"] = set()


class CyberHudBubble(QWidget):
    """
    Sci-Fi HUD диалоговое облачко в эстетике Cyberpunk:
    - Скошенный угол (chamfer) в правом верхнем углу
    - Двухцветная палитра: циан (#00f0ff) и неоново-розовый (#ff1e46)
    - Отрисовка сканлайнов (scanlines)
    - Верхний заголовок терминала [CAPRI://NET_LINK]
    - Пиксельная неоновая тень/свечение со смещением
    """

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
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_title(self, title: str) -> None:
        if self._title != title:
            self._title = title
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = self.width()
        h = self.height()
        c = self._chamfer
        so = self._shadow_offset

        bw = max(1, w - so)
        bh = max(1, h - so)

        # Контур полигона со скошенным правым верхним углом
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(bw - c, 0)
        path.lineTo(bw, c)
        path.lineTo(bw, bh)
        path.lineTo(0, bh)
        path.closeSubpath()

        # 1. Пиксельная неоновая тень/свечение со смещением (+so, +so)
        shadow_path = path.translated(so, so)
        painter.fillPath(shadow_path, QColor(255, 30, 70, 90))

        # 2. Глубокий темный фон (#08060c)
        painter.fillPath(path, QColor(8, 6, 12, 245))

        # 3. Сканлайны
        painter.save()
        painter.setClipPath(path)
        scanline_pen = QPen(QColor(0, 240, 255, 14), 1)
        painter.setPen(scanline_pen)
        for y in range(0, bh, 3):
            painter.drawLine(0, y, bw, y)
        painter.restore()

        # 4. Основная рамка (циан #00f0ff)
        cyan_pen = QPen(QColor("#00f0ff"), 2)
        painter.strokePath(path, cyan_pen)

        # 5. Акценты неоново-розовым (#ff1e46)
        accent_pen = QPen(QColor("#ff1e46"), 2)
        painter.setPen(accent_pen)
        # Подсветка скошенного угла
        painter.drawLine(bw - c, 0, bw, c)
        # Угловые засечки киберпанк HUD
        painter.drawLine(0, 0, 10, 0)
        painter.drawLine(0, 0, 0, 10)
        painter.drawLine(0, bh - 10, 0, bh)
        painter.drawLine(0, bh, 10, bh)
        painter.drawLine(bw - 10, bh, bw, bh)
        painter.drawLine(bw, bh - 10, bw, bh)

        # 6. Верхняя терминальная плашка / заголовок
        font = QFont("Press Start 2P")
        font.setPixelSize(9)
        font.setBold(True)
        painter.setFont(font)

        badge_rect = QRect(14, 5, max(10, bw - c - 20), 16)
        painter.fillRect(QRect(12, 5, 154, 16), QColor(255, 30, 70, 30))
        painter.setPen(QColor("#ff1e46"))
        painter.drawText(
            badge_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._title,
        )


class SpeechWindow(QFrame):

    revealed = Signal()

    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
        *,
        chars_per_second: float = 40.0,
        hold_ms: int = 1200,
        max_width: int = _TEXT_WIDTH,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Capri")
        self.setStyleSheet(_STYLE)

        self._text = text if text else "…"
        self._hold_ms = max(0, int(hold_ms))
        speed = max(1.0, float(chars_per_second))
        duration = len(self._text) / speed * 1000.0
        self._duration_ms = max(400.0, min(duration, 8000.0))
        self._revealed_chars = 0
        self._finished = False
        self._phase = "transmitting"
        self._transmit_frames = ["[ •     ]", "[ • •   ]", "[ • • • ]", "[   • • ]", "[     • ]"]
        self._transmit_frame_idx = 0

        self._bubble = CyberHudBubble(self)
        self._bubble.setObjectName("bubble")

        self._label = QLabel(self._bubble)
        self._label.setObjectName("text")
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setFixedWidth(max(120, int(max_width)))
        self._label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        bubble_layout = QVBoxLayout(self._bubble)
        bubble_layout.setContentsMargins(20, 28, 24, 18)
        bubble_layout.addWidget(self._label)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(self._bubble)

        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        self._transmit_timer = QTimer(self)
        self._transmit_timer.setSingleShot(True)
        self._transmit_timer.timeout.connect(self._start_message)

        self._transmit_anim_timer = QTimer(self)
        self._transmit_anim_timer.setInterval(120)
        self._transmit_anim_timer.timeout.connect(self._on_transmit_tick)

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self.close)

        self._render_transmitting()

    @property
    def text(self) -> str:
        return self._text

    @property
    def is_finished(self) -> bool:
        return self._finished

    def skip(self) -> None:
        if self._phase == "transmitting":
            self._start_message(skip_to_end=True)
        elif not self._finished:
            self._finish()
        else:
            self.close()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        if not self._clock.isValid() and self._phase == "transmitting":
            self._bubble.set_title("[CAPRI://TRANSMITTING...]")
            self._render_transmitting()
            self.adjustSize()
            self._place_randomly()
            self._transmit_anim_timer.start()
            self._transmit_timer.start(1000)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.MouseButton.LeftButton:
            self.skip()
        else:
            super().mousePressEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._transmit_timer.stop()
        self._transmit_anim_timer.stop()
        self._timer.stop()
        self._hold_timer.stop()
        super().closeEvent(event)

    def _on_transmit_tick(self) -> None:
        self._transmit_frame_idx = (
            self._transmit_frame_idx + 1
        ) % len(self._transmit_frames)
        self._render_transmitting()

    def _render_transmitting(self) -> None:
        frame = self._transmit_frames[self._transmit_frame_idx]
        self._label.setText(
            f'<span style="color:#ff1e46">TRANSMITTING</span> <span style="color:#00f0ff">{frame}</span>'
        )

    def _start_message(self, skip_to_end: bool = False) -> None:
        self._transmit_timer.stop()
        self._transmit_anim_timer.stop()
        self._phase = "typing"
        self._bubble.set_title("[CAPRI://NET_LINK]")
        get_speech_sfx().play_swoosh()

        if skip_to_end:
            self._finish()
        else:
            self._render(0)
            self.adjustSize()
            self._clock.start()
            self._timer.start()

    def _tick(self) -> None:
        if not self._clock.isValid():
            return
        progress = min(1.0, self._clock.elapsed() / self._duration_ms)
        count = round(len(self._text) * progress)
        if count != self._revealed_chars:
            self._render(count)
        if progress >= 1.0:
            self._finish()

    def _finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._timer.stop()
        self._render(len(self._text))
        self.revealed.emit()
        if self._hold_ms:
            self._hold_timer.start(self._hold_ms)
        else:
            self.close()

    def _render(self, count: int) -> None:
        count = max(0, min(count, len(self._text)))
        visible = escape(self._text[:count]).replace("\n", "<br>")
        hidden = escape(self._text[count:]).replace("\n", "<br>")
        self._label.setText(
            f'<span style="color:{_TEXT_COLOR}">{visible}</span>'
            f'<span style="color:rgba(0,0,0,0)">{hidden}</span>'
        )
        self._revealed_chars = count

    def _place_randomly(self) -> None:
        parent = self.parentWidget()
        screen = self._target_screen(parent)
        area = (
            screen.availableGeometry()
            if screen is not None
            else QRect(0, 0, self.width(), self.height())
        )
        wh = self.windowHandle()
        if wh is not None and screen is not None:
            wh.setScreen(screen)

        if parent is not None:
            # Для оверлея облика (CapriOverlayWindow) облачко всегда слева или справа
            if parent.__class__.__name__ == "CapriOverlayWindow":
                x, y = pick_side_position(
                    area, parent.frameGeometry(), self.width(), self.height()
                )
                self.move(x, y)
                return

            blocked = parent.frameGeometry().adjusted(-GAP, -GAP, GAP, GAP)
            blocked = blocked.intersected(area)
        else:
            blocked = None

        self.move(
            *pick_position(area, blocked, self.width(), self.height())
        )

    @staticmethod
    def _target_screen(parent: QWidget | None) -> QScreen | None:
        if parent is not None:
            if hasattr(parent, "get_designated_screen"):
                try:
                    scr = parent.get_designated_screen()
                    if scr is not None:
                        return scr
                except Exception:
                    pass
            wh = parent.windowHandle()
            if wh is not None and wh.screen() is not None:
                return wh.screen()
            screen = parent.screen()
            if screen is not None:
                return screen
            center = parent.frameGeometry().center()
            for s in QGuiApplication.screens():
                if s.geometry().contains(center):
                    return s
        return QGuiApplication.primaryScreen()


def show_text(
    text: str,
    parent: QWidget | None = None,
    *,
    chars_per_second: float = 40.0,
    hold_ms: int = 1200,
    max_width: int = _TEXT_WIDTH,
) -> SpeechWindow:
    window = SpeechWindow(
        text,
        parent,
        chars_per_second=chars_per_second,
        hold_ms=hold_ms,
        max_width=max_width,
    )
    _active_windows.add(window)
    window.destroyed.connect(lambda *_: _active_windows.discard(window))
    window.show()
    return window


def close_all() -> None:
    for window in list(_active_windows):
        window.close()
