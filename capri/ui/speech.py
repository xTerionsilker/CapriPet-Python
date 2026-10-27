from __future__ import annotations

from html import escape
import random
import time
from typing import Callable

from PySide6.QtCore import QElapsedTimer, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
    QScreen,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .placement import GAP, pick_position, pick_side_position
from .speech_sfx import get_speech_sfx

_TEXT_COLOR = "#00f0ff"
_TEXT_WIDTH = 420
_GLYPHS = "0123456789ABCDEF$#@%&*+-/<>~_!?░▒▓"

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

        self._glitch_mode: str | None = None
        self._glitch_intensity: float = 0.0
        self._glitch_duration = 0.2
        self._glitch_end_time = 0.0
        self._glitch_callback: Callable[[], None] | None = None

        self._glitch_timer = QTimer(self)
        self._glitch_timer.setInterval(25)
        self._glitch_timer.timeout.connect(self._on_glitch_tick)

    def set_title(self, title: str) -> None:
        if self._title != title:
            self._title = title
            self.update()

    def start_glitch(
        self,
        mode: str,
        duration_ms: int = 200,
        callback: Callable[[], None] | None = None,
    ) -> None:
        self._glitch_mode = mode
        self._glitch_duration = max(0.04, duration_ms / 1000.0)
        self._glitch_end_time = time.monotonic() + self._glitch_duration
        self._glitch_intensity = 1.0
        self._glitch_callback = callback
        self._glitch_timer.start()
        self.update()

    def stop_glitch(self) -> None:
        self._glitch_timer.stop()
        self._glitch_mode = None
        self._glitch_intensity = 0.0
        cb = self._glitch_callback
        self._glitch_callback = None
        self.update()
        if cb is not None:
            cb()

    def _on_glitch_tick(self) -> None:
        remaining = self._glitch_end_time - time.monotonic()
        if remaining <= 0:
            self.stop_glitch()
            return
        self._glitch_intensity = max(0.0, remaining / self._glitch_duration)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = self.width()
        h = self.height()
        c = self._chamfer
        so = self._shadow_offset

        is_glitch = self._glitch_mode is not None
        intensity = self._glitch_intensity if is_glitch else 0.0

        # Геометрия с легким дрожанием при глитче
        shake_x = int(random.uniform(-3, 3) * intensity) if is_glitch else 0
        bw = max(1, w - so)
        bh = max(1, h - so)

        # Контур полигона со скошенным правым верхним углом
        path = QPainterPath()
        path.moveTo(shake_x, 0)
        path.lineTo(bw - c + shake_x, 0)
        path.lineTo(bw + shake_x, c)
        path.lineTo(bw + shake_x, bh)
        path.lineTo(shake_x, bh)
        path.closeSubpath()

        # 1. Пиксельная неоновая тень/свечение со смещением (+so, +so)
        shadow_path = path.translated(so, so)
        shadow_alpha = int(90 + 50 * intensity) if is_glitch else 90
        painter.fillPath(shadow_path, QColor(255, 30, 70, shadow_alpha))

        # 2. Глубокий темный фон (#08060c)
        painter.fillPath(path, QColor(8, 6, 12, 245))

        # 3. Сканлайны (с мерцанием при глитче)
        painter.save()
        painter.setClipPath(path)
        scanline_alpha = (
            int(random.randint(15, 45) * intensity)
            if is_glitch
            else 14
        )
        scanline_pen = QPen(QColor(0, 240, 255, max(8, scanline_alpha)), 1)
        painter.setPen(scanline_pen)
        for y in range(0, bh, 3):
            painter.drawLine(0, y, bw, y)
        painter.restore()

        # 4. Хроматические RGB-аберрации при глитче
        if is_glitch and intensity > 0.1:
            dx = int(random.uniform(2, 6) * intensity)
            # Красный контур со сдвигом влево
            red_path = path.translated(-dx, 0)
            painter.strokePath(red_path, QPen(QColor(255, 30, 70, int(160 * intensity)), 2))
            # Циановый контур со сдвигом вправо
            cyan_shift = path.translated(dx, 0)
            painter.strokePath(cyan_shift, QPen(QColor(0, 240, 255, int(160 * intensity)), 2))

        # 5. Основная рамка (циан #00f0ff)
        cyan_pen = QPen(QColor("#00f0ff"), 2)
        painter.strokePath(path, cyan_pen)

        # 6. Акценты неоново-розовым (#ff1e46)
        accent_pen = QPen(QColor("#ff1e46"), 2)
        painter.setPen(accent_pen)
        # Подсветка скошенного угла
        painter.drawLine(bw - c + shake_x, 0, bw + shake_x, c)
        # Угловые засечки киберпанк HUD
        painter.drawLine(shake_x, 0, shake_x + 10, 0)
        painter.drawLine(shake_x, 0, shake_x, 10)
        painter.drawLine(shake_x, bh - 10, shake_x, bh)
        painter.drawLine(shake_x, bh, shake_x + 10, bh)
        painter.drawLine(bw - 10 + shake_x, bh, bw + shake_x, bh)
        painter.drawLine(bw + shake_x, bh - 10, bw + shake_x, bh)

        # 7. Случайные срезы (Slice Jitter) при глитче
        if is_glitch and intensity > 0.15:
            for _ in range(random.randint(2, 4)):
                sy = random.randint(0, bh - 1)
                sh = random.randint(1, 3)
                sw = random.randint(bw // 4, max(bw // 4 + 1, bw))
                sx = random.randint(0, max(0, bw - sw))
                slice_color = QColor(random.choice(("#00f0ff", "#ff1e46", "#ffffff")))
                slice_color.setAlpha(int(random.randint(40, 100) * intensity))
                painter.fillRect(sx, sy, sw, sh, slice_color)

        # 8. Верхняя терминальная плашка / заголовок
        font = QFont("Press Start 2P")
        font.setPixelSize(9)
        font.setBold(True)
        painter.setFont(font)

        badge_rect = QRect(14 + shake_x, 5, max(10, bw - c - 20), 16)
        painter.fillRect(QRect(12 + shake_x, 5, 154, 16), QColor(255, 30, 70, 30))
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

        # Предварительный расчет полной высоты для предотвращения обрезания длинных строк
        doc = QTextDocument()
        font = QFont("Press Start 2P")
        font.setPixelSize(13)
        doc.setDefaultFont(font)
        doc.setTextWidth(max(120, int(max_width)))
        doc.setHtml(escape(self._text).replace("\n", "<br>"))
        text_height = int(doc.size().height())
        self._estimated_height = max(90, text_height + 114)

        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding
        )

        self._bubble = CyberHudBubble(self)
        self._bubble.setObjectName("bubble")
        self._bubble.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding
        )

        self._label = QLabel(self._bubble)
        self._label.setObjectName("text")
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setFixedWidth(max(120, int(max_width)))
        self._label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding
        )
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
        self._hold_timer.timeout.connect(self.start_close)

        self._cursor_visible = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(480)
        self._cursor_timer.timeout.connect(self._on_cursor_tick)

        self._render_transmitting()

    @property
    def text(self) -> str:
        return self._text

    @property
    def is_finished(self) -> bool:
        return self._finished

    def skip(self) -> None:
        if self._phase == "closing":
            return
        if self._phase == "transmitting":
            self._start_message(skip_to_end=True)
        elif not self._finished:
            self._finish()
        else:
            self.start_close()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        if not self._clock.isValid() and self._phase == "transmitting":
            self._bubble.set_title("[CAPRI://TRANSMITTING...]")
            self._render_transmitting()
            self._update_geometry()
            self._place_randomly()
            self._bubble.start_glitch("open", duration_ms=180)
            self._transmit_anim_timer.start()
            self._transmit_timer.start(1000)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.MouseButton.LeftButton:
            self.skip()
        else:
            super().mousePressEvent(event)

    def start_close(self) -> None:
        """Запускает CRT-глитч закрытия, звук деактивации и плавное схлопывание."""
        if self._phase == "closing":
            return
        self._phase = "closing"
        self._timer.stop()
        self._transmit_timer.stop()
        self._transmit_anim_timer.stop()
        self._cursor_timer.stop()
        self._hold_timer.stop()

        get_speech_sfx().play_close()
        self._bubble.start_glitch(
            "close", duration_ms=200, callback=self._real_close
        )

    def _real_close(self) -> None:
        super().close()

    def close(self) -> bool:  # noqa: A003
        if self._phase != "closing":
            self.start_close()
            return True
        return super().close()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._bubble.stop_glitch()
        self._cursor_timer.stop()
        self._transmit_timer.stop()
        self._transmit_anim_timer.stop()
        self._timer.stop()
        self._hold_timer.stop()
        super().closeEvent(event)

    def _on_cursor_tick(self) -> None:
        self._cursor_visible = not self._cursor_visible
        self._render_finished()

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

    def _update_geometry(self) -> None:
        """Пересчитывает размер окна и удерживает его в пределах экрана."""
        self.adjustSize()
        screen = self._target_screen(self.parentWidget())
        if screen is not None:
            area = screen.availableGeometry()
            if self.y() + self.height() > area.bottom() - 15:
                new_y = max(area.top() + 15, area.bottom() - self.height() - 15)
                self.move(self.x(), new_y)

    def _start_message(self, skip_to_end: bool = False) -> None:
        self._transmit_timer.stop()
        self._transmit_anim_timer.stop()
        self._phase = "typing"
        self._bubble.set_title("[CAPRI://NET_LINK]")
        get_speech_sfx().play_swoosh()

        if skip_to_end:
            self._finish()
        else:
            self._render_scramble(0)
            self._update_geometry()
            self._clock.start()
            self._timer.start()

    def _tick(self) -> None:
        if not self._clock.isValid():
            return
        progress = min(1.0, self._clock.elapsed() / self._duration_ms)
        count = round(len(self._text) * progress)
        self._render_scramble(count)
        get_speech_sfx().play_chirp()
        if progress >= 1.0:
            self._finish()

    def _finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._phase = "holding"
        self._timer.stop()
        self._cursor_visible = True
        self._render_finished()
        self._cursor_timer.start(480)
        self.revealed.emit()
        if self._hold_ms:
            self._hold_timer.start(self._hold_ms)
        else:
            self.start_close()

    def _render_scramble(self, fixed_count: int) -> None:
        fixed_count = max(0, min(fixed_count, len(self._text)))
        scramble_count = min(3, len(self._text) - fixed_count)
        scramble_end = fixed_count + scramble_count

        fixed_part = escape(self._text[:fixed_count]).replace("\n", "<br>")

        scramble_chars: list[str] = []
        for ch in self._text[fixed_count:scramble_end]:
            if ch in ("\n", " ", "\t"):
                scramble_chars.append(ch)
            else:
                scramble_chars.append(random.choice(_GLYPHS))
        scramble_part = escape("".join(scramble_chars)).replace("\n", "<br>")

        cursor = '<span style="color:#ff1e46">█</span>'
        hidden_part = escape(self._text[scramble_end:]).replace("\n", "<br>")

        html = (
            f'<span style="color:{_TEXT_COLOR}">{fixed_part}</span>'
            f'<span style="color:#ff1e46">{scramble_part}</span>'
            f'{cursor}'
            f'<span style="color:rgba(0,0,0,0)">{hidden_part}</span>'
        )
        self._label.setText(html)
        self._revealed_chars = fixed_count
        self._update_geometry()

    def _render_finished(self) -> None:
        visible = escape(self._text).replace("\n", "<br>")
        cursor_color = "#ff1e46" if self._cursor_visible else "rgba(0,0,0,0)"
        self._label.setText(
            f'<span style="color:{_TEXT_COLOR}">{visible}</span>'
            f'<span style="color:{cursor_color}">█</span>'
        )
        self._revealed_chars = len(self._text)
        self._update_geometry()

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

        target_height = max(self.height(), self._estimated_height)

        if parent is not None:
            # Для оверлея облика (CapriOverlayWindow) облачко всегда слева или справа
            if parent.__class__.__name__ == "CapriOverlayWindow":
                x, y = pick_side_position(
                    area, parent.frameGeometry(), self.width(), target_height
                )
                if y + target_height > area.bottom() - 15:
                    y = max(area.top() + 15, area.bottom() - target_height - 15)
                self.move(x, y)
                return

            blocked = parent.frameGeometry().adjusted(-GAP, -GAP, GAP, GAP)
            blocked = blocked.intersected(area)
        else:
            blocked = None

        px, py = pick_position(area, blocked, self.width(), target_height)
        if py + target_height > area.bottom() - 15:
            py = max(area.top() + 15, area.bottom() - target_height - 15)
        self.move(px, py)

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
