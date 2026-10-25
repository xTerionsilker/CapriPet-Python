"""Click-through full-screen glitch overlay.

Creates one frameless, input-transparent window per screen. Artifacts are
always present at a low, subtle level, with no periodic intensification.
Each overlay reports how intense its current frame is through the
``amplitude_changed`` signal, which drives the background static in
``capri.static_noise``.
It is purely decorative: clicks, scrolling and keyboard input go straight
through to the windows underneath.

On platforms that do not support click-through/always-on-top windows (some
Wayland compositors), the overlay may be limited or not appear at all.
"""

from __future__ import annotations

import random

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QScreen
from PySide6.QtWidgets import QWidget

_COLORS = ("#39ff6a", "#ff1e46", "#a259ff", "#eaffef")
_NOISE = ("#39ff6a", "#ff1e46", "#ffffff", "#a259ff")
_BASE_INTERVAL_MS = 66  # ~15 fps for the subtle layer


class GlitchOverlay(QWidget):
    """A transparent, click-through window that paints continuous glitches."""

    amplitude_changed = Signal(float)

    def __init__(self, screen: QScreen) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(None, flags)
        self._screen = screen
        self.setWindowTitle("Capri glitch overlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(screen.geometry())
        screen.geometryChanged.connect(self._sync_geometry)

        self._active = True
        self._amplitude = 0.0

        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(_BASE_INTERVAL_MS)
        self._frame_timer.timeout.connect(self._tick)
        self._frame_timer.start()

    # --- timing ------------------------------------------------------------
    def set_active(self, active: bool) -> None:
        """Show/hide the overlay and pause/resume its timers."""
        if active == self._active:
            return
        self._active = active
        if active:
            self._frame_timer.start()
            self.show()
        else:
            self._frame_timer.stop()
            self._set_amplitude(0.0)
            self.hide()

    def _sync_geometry(self, *_args) -> None:
        self.setGeometry(self._screen.geometry())

    def _tick(self) -> None:
        self._update_amplitude()
        self.update()

    # --- intensity ---------------------------------------------------------
    def _update_amplitude(self) -> None:
        """Report how violent the current frame is, from 0.0 to 1.0.

        The static audio layer listens to this. The subtle layer flickers a
        little so it never feels like a frozen sample.
        """
        if not self._active:
            self._set_amplitude(0.0)
        else:
            self._set_amplitude(random.uniform(0.0, 0.12))

    def _set_amplitude(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        if abs(value - self._amplitude) < 0.02:
            return
        self._amplitude = value
        self.amplitude_changed.emit(value)

    # --- painting ----------------------------------------------------------
    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            painter.end()
            return

        # Every frame starts from a clean transparent buffer so artifacts do
        # not accumulate into an opaque mess.
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Clear
        )
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )

        self._paint_tears(painter, width, height)
        self._paint_slices(painter, width, height)
        self._paint_scanlines(painter, width, height)
        self._paint_noise(painter, width, height)
        self._paint_bars(painter, width, height)

        painter.end()

    def _paint_tears(self, painter: QPainter, width: int, height: int) -> None:
        count = 1 if random.random() < 0.45 else 0
        for _ in range(count):
            y = random.randint(0, height - 1)
            band = random.randint(1, 4)
            tint = QColor(random.choice(_COLORS))
            tint.setAlpha(random.randint(10, 22))
            painter.fillRect(0, y, width, band, tint)

    def _paint_slices(self, painter: QPainter, width: int, height: int) -> None:
        count = random.randint(2, 6)
        for _ in range(count):
            y = random.randint(0, height - 1)
            slice_height = random.randint(1, 3)
            slice_width = random.randint(
                width // 12, max(width // 12 + 1, width // 2)
            )
            x = random.randint(0, max(0, width - slice_width))
            color = QColor(random.choice(_COLORS))
            color.setAlpha(random.randint(14, 34))
            painter.fillRect(x, y, slice_width, slice_height, color)

            ghost = QColor(color)
            ghost.setAlpha(max(4, color.alpha() // 3))
            painter.fillRect(
                max(0, min(width - 1, x + random.randint(-120, 120))),
                y,
                min(slice_width, width),
                1,
                ghost,
            )

    def _paint_scanlines(
        self, painter: QPainter, width: int, height: int
    ) -> None:
        alpha = random.randint(7, 13)
        painter.setPen(QPen(QColor(57, 255, 106, alpha)))
        for y in range(0, height, 3):
            painter.drawLine(0, y, width, y)

    def _paint_noise(self, painter: QPainter, width: int, height: int) -> None:
        base = max(18, min(80, width * height // 60000))
        count = random.randint(int(base * 0.8), int(base * 1.3))
        count = min(count, 1300)
        for _ in range(count):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            fleck = QColor(random.choice(_NOISE))
            fleck.setAlpha(random.randint(30, 80))
            painter.fillRect(x, y, 1, 1, fleck)

    def _paint_bars(self, painter: QPainter, width: int, height: int) -> None:
        if random.random() >= 0.06:
            return
        y = random.randint(0, height - 1)
        main = QColor(random.choice(_COLORS[:3]))
        main.setAlpha(60)
        painter.fillRect(0, y, width, 1, main)
        fringe = QColor(random.choice(_COLORS[:3]))
        fringe.setAlpha(35)
        painter.fillRect(0, y + 1, width, 1, fringe)
        painter.fillRect(0, max(0, y - 1), width, 1, fringe)


class GlitchManager(QObject):
    """Keeps one glitch overlay alive on every connected screen."""

    amplitude_changed = Signal(float)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._overlays: dict[QScreen, GlitchOverlay] = {}
        self._amplitudes: dict[QScreen, float] = {}
        self._enabled = True

        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(self._add_screen)
            app.screenRemoved.connect(self._remove_screen)
        for screen in QGuiApplication.screens():
            self._add_screen(screen)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Turn the overlays on or off without destroying them."""
        if enabled == self._enabled:
            return
        self._enabled = enabled
        for overlay in self._overlays.values():
            overlay.set_active(enabled)

    def toggle(self) -> bool:
        """Flip the overlay state and return the new state."""
        self.set_enabled(not self._enabled)
        return self._enabled

    def _add_screen(self, screen: QScreen) -> None:
        if screen in self._overlays:
            return
        overlay = GlitchOverlay(screen)
        overlay.amplitude_changed.connect(
            lambda value, s=screen: self._on_amplitude(s, value)
        )
        if self._enabled:
            overlay.show()
        else:
            overlay.set_active(False)
        self._overlays[screen] = overlay

    def _on_amplitude(self, screen: QScreen, value: float) -> None:
        self._amplitudes[screen] = value
        self.amplitude_changed.emit(max(self._amplitudes.values(), default=0.0))

    def _remove_screen(self, screen: QScreen) -> None:
        overlay = self._overlays.pop(screen, None)
        self._amplitudes.pop(screen, None)
        if overlay is not None:
            overlay.close()
            overlay.deleteLater()
        self.amplitude_changed.emit(max(self._amplitudes.values(), default=0.0))

    def stop(self) -> None:
        """Close every overlay and stop painting."""
        app = QGuiApplication.instance()
        if app is not None:
            for signal, slot in (
                (app.screenAdded, self._add_screen),
                (app.screenRemoved, self._remove_screen),
            ):
                try:
                    signal.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass
        for overlay in self._overlays.values():
            overlay.close()
            overlay.deleteLater()
        self._overlays.clear()
        self._amplitudes.clear()
