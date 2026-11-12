"""Диалоговые облака и система вывода реплик питомца Capri.

Реализует HUD-бабл в стиле киберпанк (CyberHudBubble), эффект печатной
машинки с глитчами и плавающее окно диалога (SpeechWindow).
"""

from __future__ import annotations

import contextlib
import random
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
    QGuiApplication,
    QScreen,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .pet_renderer import pick_adjacent_position
from .speech_bubble import CyberHudBubble
from .speech_sfx import get_speech_sfx
from .theme import (
    ACID_GREEN,
    NEON_CRIMSON,
    PIXEL_FONT,
    PURE_WHITE,
    get_terminal_font,
)

__all__ = [
    "CyberHudBubble",
    "SpeechWindow",
    "close_all",
    "has_active_speech",
    "is_speech_suppressed",
    "set_speech_suppressed",
    "show_text",
]

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
        is_excited = "!" in self._text or any(
            w.isupper() and len(w) > 2 for w in self._text.split()
        )
        self._bubble.set_excited(is_excited)
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

        for w in QApplication.topLevelWidgets():
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
                with contextlib.suppress(Exception):
                    scr = parent.get_designated_screen()
                    if scr is not None:
                        return scr
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
