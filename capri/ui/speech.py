"""Диалоговые облака и система вывода реплик питомца Capri.

Реализует HUD-бабл в стиле киберпанк (CyberHudBubble), эффект печатной
машинки с глитчами и плавающее окно диалога (SpeechWindow).
"""

from __future__ import annotations

import contextlib
import random
import time
from collections.abc import Callable
from html import escape

from PySide6.QtCore import (
    QElapsedTimer,
    QEvent,
    QObject,
    QRect,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
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

from .pet_renderer import pick_adjacent_position
from .speech_sfx import get_speech_sfx
from .theme import (
    ACID_GREEN,
    ELECTRIC_BLUE,
    NEON_CRIMSON,
    PIXEL_FONT,
    PURE_WHITE,
    get_hud_font,
    get_terminal_font,
)

_TEXT_COLOR = PURE_WHITE
_TEXT_WIDTH = 420
_GLYPHS = "0123456789ABCDEF$#@%&*+-/<>~_!?░▒▓"
_SUPPRESSED = False

_STYLE = f"""
QLabel#text {{
    background: transparent;
    color: {_TEXT_COLOR};
    font-family: {PIXEL_FONT};
    font-size: 13px;
    letter-spacing: 1px;
}}
"""

_active_windows: set[SpeechWindow] = set()

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

        dir_ = self._pointer_direction
        path = QPainterPath()
        path.moveTo(shake_x, 0)

        if dir_ == "up":
            path.lineTo(x_mid - 12 + shake_x, 0)
            path.lineTo(x_mid - 5 + shake_x, 6)
            path.lineTo(x_mid + 5 + shake_x, 6)
            path.lineTo(x_mid + 12 + shake_x, 0)
        path.lineTo(bw - c + shake_x, 0)

        path.lineTo(bw + shake_x, c)

        if dir_ == "right":
            path.lineTo(bw + shake_x, y_mid - 12)
            path.lineTo(bw + shake_x - 6, y_mid - 5)
            path.lineTo(bw + shake_x - 6, y_mid + 5)
            path.lineTo(bw + shake_x, y_mid + 12)
        path.lineTo(bw + shake_x, bh)

        if dir_ == "down":
            path.lineTo(x_mid + 12 + shake_x, bh)
            path.lineTo(x_mid + 5 + shake_x, bh - 6)
            path.lineTo(x_mid - 5 + shake_x, bh - 6)
            path.lineTo(x_mid - 12 + shake_x, bh)
        path.lineTo(shake_x, bh)

        if dir_ == "left":
            path.lineTo(shake_x, y_mid + 12)
            path.lineTo(shake_x + 6, y_mid + 5)
            path.lineTo(shake_x + 6, y_mid - 5)
            path.lineTo(shake_x, y_mid - 12)
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

        painter.drawLine(bw - c + shake_x, 0, bw + shake_x, c)

        painter.drawLine(shake_x, 0, shake_x + 10, 0)
        painter.drawLine(shake_x, 0, shake_x, 10)
        painter.drawLine(shake_x, bh - 10, shake_x, bh)
        painter.drawLine(shake_x, bh, shake_x + 10, bh)
        painter.drawLine(bw - 10 + shake_x, bh, bw + shake_x, bh)
        painter.drawLine(bw + shake_x, bh - 10, bw + shake_x, bh)

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

        badge_rect = QRect(14 + shake_x, 5, max(10, bw - c - 20), 16)
        painter.fillRect(
            QRect(12 + shake_x, 5, 168, 16), QColor(246, 2, 63, 35)
        )
        painter.setPen(QColor(ACID_GREEN))
        chevron = _CHEVRONS.get(dir_, "")
        title_with_dir = f"{self._title} {chevron}".strip()
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


class SpeechWindow(QFrame):
    """Плавающее окно диалога с посимвольным выводом текста реплики питомца."""

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
        self._phase = "opening"

        self._target_widget: QWidget | None = self._resolve_target(parent)
        self._current_active_target: QWidget | None = self._target_widget
        self._last_target_geom: QRect | None = None
        self._side: str = "right"

        self.setWindowOpacity(0.0)

        doc = QTextDocument()
        font = get_terminal_font(13, bold=True)
        doc.setDefaultFont(font)
        doc.setTextWidth(max(120, int(max_width)))
        doc.setHtml(escape(self._text).replace("\n", "<br>"))
        text_height = int(doc.size().height())
        self._estimated_height = max(90, text_height + 96)

        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.MinimumExpanding,
        )

        self._bubble = CyberHudBubble(self)
        self._bubble.setObjectName("bubble")
        self._bubble.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.MinimumExpanding,
        )

        self._label = QLabel(self._bubble)
        self._label.setObjectName("text")
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setFixedWidth(max(120, int(max_width)))
        self._label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.MinimumExpanding,
        )
        self._label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self._label.setVisible(False)

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

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self.start_close)

        self._cursor_visible = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(480)
        self._cursor_timer.timeout.connect(self._on_cursor_tick)

        self._follow_timer = QTimer(self)
        self._follow_timer.setInterval(25)
        self._follow_timer.timeout.connect(self._check_and_follow_target)

        if self._current_active_target is not None:
            with contextlib.suppress(Exception):
                self._current_active_target.installEventFilter(self)

    @property
    def text(self) -> str:
        return self._text

    @property
    def is_finished(self) -> bool:
        return self._finished

    @classmethod
    def _resolve_target(cls, widget: QWidget | None) -> QWidget | None:

        if widget is not None:
            return widget

        app = QGuiApplication.instance()
        if app is not None:
            for w in app.topLevelWidgets():
                if w.isVisible() and w.__class__.__name__ == "CapriWindow":
                    return w
        return None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._current_active_target:
            if event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
                self._check_and_follow_target()
            elif event.type() == QEvent.Type.Hide:
                QTimer.singleShot(15, self._check_and_follow_target)
        return super().eventFilter(watched, event)

    def _check_and_follow_target(self) -> None:

        if self._phase == "closing":
            return

        active = self._resolve_target(self._target_widget)
        if active is not self._current_active_target:
            if self._current_active_target is not None:
                with contextlib.suppress(Exception):
                    self._current_active_target.removeEventFilter(self)
            self._current_active_target = active
            if self._current_active_target is not None:
                with contextlib.suppress(Exception):
                    self._current_active_target.installEventFilter(self)
            self._place_next_to_target(keep_side=False)
            return

        if active is not None and active.isVisible():
            cur_geom = active.frameGeometry()
            if (
                self._last_target_geom is None
                or cur_geom != self._last_target_geom
            ):
                self._place_next_to_target(keep_side=True)

    def update_anim_opacity(self, phase: str, progress: float) -> None:

        if phase == "opening":
            opacity = min(1.0, max(0.0, progress * 1.5))
            self.setWindowOpacity(opacity)
            if progress < 0.28:
                if self._label.isVisible():
                    self._label.setVisible(False)
            else:
                if (
                    not self._label.isVisible()
                    and self._phase != "closing"
                ):
                    self._label.setVisible(True)
        elif phase == "closing":
            opacity = max(0.0, min(1.0, (1.0 - progress) ** 1.4))
            self.setWindowOpacity(opacity)
            if self._label.isVisible():
                self._label.setVisible(False)

    def skip(self) -> None:
        if self._phase == "closing":
            self._real_close()
            return
        if (
            self._phase == "opening"
            or self._bubble.anim_phase == "opening"
        ):
            self._bubble.stop_animations()
            self.setWindowOpacity(1.0)
            self._bubble.anim_phase = "idle"
            self._on_bubble_opened()
            return
        if not self._finished:
            self._finish()
        else:
            self.start_close()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._clock.isValid() and self._phase == "opening":
            self._bubble.set_title("[CAPRI://NET_LINK]")
            self._render_scramble(0)
            self._update_geometry()
            self._place_next_to_target(keep_side=False)
            get_speech_sfx().play_swoosh()
            self._follow_timer.start()
            self._bubble.start_open(
                duration_ms=250, callback=self._on_bubble_opened
            )

    def _on_bubble_opened(self) -> None:

        self._phase = "typing"
        self._label.setVisible(True)
        self._render_scramble(0)
        self._update_geometry()
        self._clock.start()
        self._timer.start()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.skip()
        else:
            super().mousePressEvent(event)

    def start_close(self) -> None:

        if self._phase == "closing":
            return
        self._phase = "closing"
        self._follow_timer.stop()
        self._timer.stop()
        self._cursor_timer.stop()
        self._hold_timer.stop()

        if self._current_active_target is not None:
            with contextlib.suppress(Exception):
                self._current_active_target.removeEventFilter(self)

        get_speech_sfx().play_close()
        self._bubble.start_close(
            duration_ms=220, callback=self._real_close
        )

    def _real_close(self) -> None:
        super().close()

    def close(self, immediate: bool = False) -> bool:
        if immediate:
            self._real_close()
            return True
        if self._phase != "closing":
            self.start_close()
            return True
        return super().close()

    def closeEvent(self, event) -> None:
        self._follow_timer.stop()
        self._bubble.stop_animations()
        self._cursor_timer.stop()
        self._timer.stop()
        self._hold_timer.stop()
        if self._current_active_target is not None:
            with contextlib.suppress(Exception):
                self._current_active_target.removeEventFilter(self)
        super().closeEvent(event)

    def _on_cursor_tick(self) -> None:
        self._cursor_visible = not self._cursor_visible
        self._render_finished()

    def _update_geometry(self) -> None:

        self.adjustSize()
        self._place_next_to_target(keep_side=True)

    def _tick(self) -> None:
        if not self._clock.isValid():
            return
        progress = min(1.0, self._clock.elapsed() / self._duration_ms)
        count = round(len(self._text) * progress)
        self._render_scramble(count)
        current_char = self._text[count - 1] if 0 < count <= len(self._text) else ""
        get_speech_sfx().play_chirp(current_char)
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
        scramble_part = escape("".join(scramble_chars)).replace(
            "\n", "<br>"
        )

        cursor = f'<span style="color:{NEON_CRIMSON}">█</span>'
        hidden_part = escape(self._text[scramble_end:]).replace(
            "\n", "<br>"
        )

        html = (
            f'<span style="color:{_TEXT_COLOR}">{fixed_part}</span>'
            f'<span style="color:{ACID_GREEN}">{scramble_part}</span>'
            f"{cursor}"
            f'<span style="color:rgba(0,0,0,0)">{hidden_part}</span>'
        )
        self._label.setText(html)
        self._revealed_chars = fixed_count

    def _render_finished(self) -> None:
        visible = escape(self._text).replace("\n", "<br>")
        cursor_color = (
            NEON_CRIMSON if self._cursor_visible else "rgba(0,0,0,0)"
        )
        self._label.setText(
            f'<span style="color:{_TEXT_COLOR}">{visible}</span>'
            f'<span style="color:{cursor_color}">█</span>'
        )
        self._revealed_chars = len(self._text)

    def _place_next_to_target(self, keep_side: bool = False) -> None:

        target = self._current_active_target
        if target is None:
            target = self._resolve_target(self.parentWidget())
            self._current_active_target = target

        screen = self._target_screen(target)
        area = (
            screen.availableGeometry()
            if screen is not None
            else QRect(0, 0, 1920, 1080)
        )
        wh = self.windowHandle()
        if wh is not None and screen is not None:
            wh.setScreen(screen)

        target_height = max(self.height(), self._estimated_height)
        bubble_width = max(self.width(), self._label.width() + 48)

        if target is not None and target.isVisible():
            target_rect = target.frameGeometry()
            pref_side = self._side if keep_side else None
            px, py, chosen_side = pick_adjacent_position(
                area,
                target_rect,
                bubble_width,
                target_height,
                gap=16,
                preferred_side=pref_side,
            )
            self._side = chosen_side

            dir_to_capri = {
                "right": "left",
                "left": "right",
                "top": "down",
                "bottom": "up",
            }.get(chosen_side, "left")
            self._bubble.set_pointer_direction(dir_to_capri)
            self._last_target_geom = target_rect
        else:
            px = area.right() - bubble_width - 24
            py = area.bottom() - target_height - 24
            self._bubble.set_pointer_direction("none")

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


class _SpeechManager:
    suppressed: bool = False


def is_speech_suppressed() -> bool:
    return _SpeechManager.suppressed


def set_speech_suppressed(suppressed: bool) -> None:
    _SpeechManager.suppressed = bool(suppressed)
    if _SpeechManager.suppressed:
        close_all()


def show_text(
    text: str,
    parent: QWidget | None = None,
    *,
    chars_per_second: float = 40.0,
    hold_ms: int = 1200,
    max_width: int = _TEXT_WIDTH,
) -> SpeechWindow | None:
    if _SpeechManager.suppressed:
        return None
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


def has_active_speech() -> bool:

    return any(w.isVisible() for w in _active_windows)


def close_all() -> None:
    for window in list(_active_windows):
        window.close()
