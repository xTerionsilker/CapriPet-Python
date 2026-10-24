"""Reusable typewriter speech window.

Shows a short message character by character, then closes itself after the
text has been fully revealed. It is intentionally self-contained (PySide6
only) so it can be reused outside Capri.

Usage::

    from capri.speech import show_text

    show_text("Hello there!", parent=window)
    show_text("Faster and shorter", chars_per_second=80, hold_ms=500)

Clicking the window while text is appearing reveals the rest instantly;
clicking again closes it. The window also closes after ``hold_ms``.

The text is wrapped in a transparent span while hidden so the bubble does not
resize or reflow while it is being typed out.
"""

from __future__ import annotations

from html import escape

from PySide6.QtCore import QElapsedTimer, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

_TEXT_COLOR = "#eaffef"
_TEXT_WIDTH = 420

_STYLE = """
QFrame#bubble {
    background: #f708060c;
    border: 1px solid #39ff6a;
    border-radius: 14px;
}
QLabel#text {
    background: transparent;
    color: #eaffef;
    font-family: "JetBrains Mono", "DejaVu Sans Mono", monospace;
    font-size: 14px;
}
"""

# Keep fire-and-forget windows alive until Qt deletes them.
_active_windows: set["SpeechWindow"] = set()


class SpeechWindow(QFrame):
    """A frameless bubble that types out ``text`` and closes itself."""

    revealed = Signal()

    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
        *,
        anchor: QWidget | None = None,
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

        self._anchor = anchor
        self._text = text if text else "…"
        self._hold_ms = max(0, int(hold_ms))
        speed = max(1.0, float(chars_per_second))
        duration = len(self._text) / speed * 1000.0
        self._duration_ms = max(400.0, min(duration, 8000.0))
        self._revealed_chars = 0
        self._finished = False

        bubble = QFrame(self)
        bubble.setObjectName("bubble")
        bubble.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._label = QLabel(bubble)
        self._label.setObjectName("text")
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setFixedWidth(max(120, int(max_width)))
        self._label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(24, 20, 24, 20)
        bubble_layout.addWidget(self._label)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 22, 22, 22)
        outer.addWidget(bubble)

        glow = QGraphicsDropShadowEffect(bubble)
        glow.setBlurRadius(32)
        glow.setOffset(0, 0)
        glow.setColor(QColor(57, 255, 106, 130))
        bubble.setGraphicsEffect(glow)

        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self.close)

        self._render(0)

    # --- public API --------------------------------------------------------
    @property
    def text(self) -> str:
        return self._text

    @property
    def is_finished(self) -> bool:
        return self._finished

    def skip(self) -> None:
        """Reveal everything now and start the auto-close countdown."""
        if self._finished:
            self.close()
        else:
            self._finish()

    # --- Qt events ---------------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        if not self._clock.isValid():
            self.adjustSize()
            self._center_on_parent()
            self._clock.start()
            self._timer.start()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.MouseButton.LeftButton:
            self.skip()
        else:
            super().mousePressEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._timer.stop()
        self._hold_timer.stop()
        super().closeEvent(event)

    # --- internals ---------------------------------------------------------
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

    def _center_on_parent(self) -> None:
        reference = self._anchor if self._anchor is not None else self.parentWidget()
        if reference is not None:
            center = reference.frameGeometry().center()
        else:
            screen = QGuiApplication.primaryScreen()
            center = (
                screen.availableGeometry().center()
                if screen is not None
                else self.rect().center()
            )
        self.move(
            center.x() - self.width() // 2,
            center.y() - self.height() // 2,
        )


def show_text(
    text: str,
    parent: QWidget | None = None,
    *,
    anchor: QWidget | None = None,
    chars_per_second: float = 40.0,
    hold_ms: int = 1200,
    max_width: int = _TEXT_WIDTH,
) -> SpeechWindow:
    """Show ``text`` in a self-closing typewriter bubble and return the window.

    ``chars_per_second`` controls the reveal speed, ``hold_ms`` is how long the
    fully revealed text stays on screen, and ``max_width`` caps the text width.
    Pass ``anchor`` to centre the bubble on a specific widget of ``parent``
    instead of the parent window itself.
    """
    window = SpeechWindow(
        text,
        parent,
        anchor=anchor,
        chars_per_second=chars_per_second,
        hold_ms=hold_ms,
        max_width=max_width,
    )
    _active_windows.add(window)
    window.destroyed.connect(lambda *_: _active_windows.discard(window))
    window.show()
    return window
