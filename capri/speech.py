"""Многоразовое окно речи с эффектом печатной машинки.

Показывает короткое сообщение посимвольно, затем закрывается после полного
раскрытия текста. Оно намеренно самодостаточно (только PySide6), поэтому
его можно использовать и вне Capri.

Использование::

    from capri.speech import show_text

    show_text("Привет!", parent=window)
    show_text("Быстрее и короче", chars_per_second=80, hold_ms=500)

Облачко появляется в случайном месте экрана, не перекрывая окно ``parent``
(которое считается главным окном программы). Для этого нужна платформа,
уважающая перемещение окон: X11/XWayland подходит; в чистом Wayland место
выбирает композитор.

Клик по окну во время появления текста сразу раскрывает остаток; повторный
клик закрывает. Окно также закрывается через ``hold_ms``.

Пока текст скрыт, он обёрнут в прозрачный фрагмент, чтобы облачко не
меняло размер и не перестраивалось во время печати.

Геометрия случайного места (полосы свободного экрана, наименьшее
перекрытие) вынесена в ``capri.placement``.
"""

from __future__ import annotations

from html import escape

from PySide6.QtCore import QElapsedTimer, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QScreen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .placement import GAP, pick_position

_TEXT_COLOR = "#eaffef"
_TEXT_WIDTH = 420

_STYLE = """
QFrame#bubble {
    background: #f708060c;
    border: 3px solid #39ff6a;
    border-radius: 0;
}
QLabel#text {
    background: transparent;
    color: #eaffef;
    font-family: "Press Start 2P", "Pixelify Sans", "VT323", "Terminus",
        "JetBrains Mono", "DejaVu Sans Mono", monospace;
    font-size: 14px;
    letter-spacing: 1px;
}
"""

# Держим окна «выстрелил и забыл» живыми, пока Qt их не удалит.
_active_windows: set["SpeechWindow"] = set()


class SpeechWindow(QFrame):
    """Облачко без рамки, печатающее ``text`` и закрывающееся само."""

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
        # Жёсткая несмазанная тень со смещением вместо мягкого неонового свечения.
        glow.setBlurRadius(0)
        glow.setOffset(8, 8)
        glow.setColor(QColor(57, 255, 106, 110))
        bubble.setGraphicsEffect(glow)
        if sys.platform.startswith("win"):
            # На Windows QGraphicsEffect включает для окна режим UpdateLayeredWindow
            # (per-pixel alpha). Без него WA_TranslucentBackground даёт лишь
            # chroma-key — вокруг облачка проступает чужой «зелёный» экран.
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)

        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self.close)

        self._render(0)

    # --- публичное API -----------------------------------------------------
    @property
    def text(self) -> str:
        return self._text

    @property
    def is_finished(self) -> bool:
        return self._finished

    def skip(self) -> None:
        """Раскрыть всё сразу и запустить обратный отсчёт закрытия."""
        if self._finished:
            self.close()
        else:
            self._finish()

    # --- события Qt --------------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        if not self._clock.isValid():
            self.adjustSize()
            self._place_randomly()
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

    # --- внутреннее --------------------------------------------------------
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
        """Выбрать случайное место на экране вне главного окна."""
        parent = self.parentWidget()
        screen = self._target_screen(parent)
        area = (
            screen.availableGeometry()
            if screen is not None
            else QRect(0, 0, self.width(), self.height())
        )

        # Небольшой визуальный зазор между облачком и главным окном.
        blocked = None
        if parent is not None:
            blocked = parent.frameGeometry().adjusted(-GAP, -GAP, GAP, GAP)
            blocked = blocked.intersected(area)

        self.move(
            *pick_position(area, blocked, self.width(), self.height())
        )

    @staticmethod
    def _target_screen(parent: QWidget | None) -> QScreen | None:
        if parent is not None:
            screen = parent.screen()
            if screen is not None:
                return screen
        return QGuiApplication.primaryScreen()


def show_text(
    text: str,
    parent: QWidget | None = None,
    *,
    chars_per_second: float = 40.0,
    hold_ms: int = 1200,
    max_width: int = _TEXT_WIDTH,
) -> SpeechWindow:
    """Показать ``text`` в самозакрывающемся облачке и вернуть окно.

    ``chars_per_second`` задаёт скорость раскрытия, ``hold_ms`` — сколько
    полностью раскрытый текст остаётся на экране, а ``max_width``
    ограничивает ширину текста. Облачко размещается в случайной точке на
    экране родительского окна, не перекрывая его.
    """
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
