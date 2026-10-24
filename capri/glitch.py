"""Click-through full-screen glitch overlay.

Creates one frameless, input-transparent window per screen. Artifacts are
always present at a low, subtle level; every few seconds the amplitude spikes
into a short, violent burst of tears, noise, flashes and colour fringing.
It is purely decorative: clicks, scrolling and keyboard input go straight
through to the windows underneath.

On platforms that do not support click-through/always-on-top windows (some
Wayland compositors), the overlay may be limited or not appear at all.
"""

from __future__ import annotations

import random

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QScreen
from PySide6.QtWidgets import QWidget

_COLORS = ("#39ff6a", "#ff1e46", "#a259ff", "#eaffef")
_NOISE = ("#39ff6a", "#ff1e46", "#ffffff", "#a259ff")
_BASE_INTERVAL_MS = 66   # ~15 fps for the constant subtle layer
_SPIKE_INTERVAL_MS = 33  # ~30 fps while the amplitude spikes


class GlitchOverlay(QWidget):
    """A transparent, click-through window that paints continuous glitches."""

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

        self._spike_frames = 0

        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(_BASE_INTERVAL_MS)
        self._frame_timer.timeout.connect(self._tick)
        self._frame_timer.start()

        self._spike_timer = QTimer(self)
        self._spike_timer.setSingleShot(True)
        self._spike_timer.timeout.connect(self._start_spike)
        self._spike_timer.start(random.randint(3000, 6500))

    # --- timing ------------------------------------------------------------
    def _sync_geometry(self, *_args) -> None:
        self.setGeometry(self._screen.geometry())

    def _tick(self) -> None:
        self.update()
        if self._spike_frames > 0:
            self._spike_frames -= 1
            if self._spike_frames == 0:
                self._frame_timer.setInterval(_BASE_INTERVAL_MS)
                self._spike_timer.start(random.randint(3500, 8000))

    def _start_spike(self) -> None:
        duration_ms = random.randint(280, 850)
        self._spike_frames = max(1, round(duration_ms / _SPIKE_INTERVAL_MS))
        self._frame_timer.setInterval(_SPIKE_INTERVAL_MS)
        self.update()

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

        spike = self._spike_frames > 0

        if spike:
            self._paint_spike_wash(painter, width, height)

        self._paint_tears(painter, width, height, spike)
        self._paint_slices(painter, width, height, spike)
        self._paint_scanlines(painter, width, height, spike)
        self._paint_noise(painter, width, height, spike)
        self._paint_bars(painter, width, height, spike)
        if spike:
            self._paint_spike_blocks(painter, width, height)

        painter.end()

    def _paint_spike_wash(self, painter: QPainter, width: int, height: int) -> None:
        wash = QColor(random.choice(_COLORS))
        wash.setAlpha(random.randint(12, 55))
        painter.fillRect(0, 0, width, height, wash)

        roll = random.random()
        if roll < 0.22:
            flash = QColor(255, 255, 255)
            flash.setAlpha(random.randint(25, 90))
            painter.fillRect(0, 0, width, height, flash)
        elif roll < 0.34:
            blackout = QColor(0, 0, 0)
            blackout.setAlpha(random.randint(20, 70))
            painter.fillRect(0, 0, width, height, blackout)

        # Heavy dropped-signal bands.
        for _ in range(random.randint(1, 3)):
            y = random.randint(0, height - 1)
            band = random.randint(10, max(11, height // 12))
            blackout = QColor(0, 0, 0)
            blackout.setAlpha(random.randint(40, 150))
            painter.fillRect(0, y, width, band, blackout)

    def _paint_tears(
        self, painter: QPainter, width: int, height: int, spike: bool
    ) -> None:
        count = random.randint(3, 6) if spike else (1 if random.random() < 0.3 else 0)
        for _ in range(count):
            y = random.randint(0, height - 1)
            band = random.randint(1, 26) if spike else random.randint(1, 3)
            tint = QColor(random.choice(_COLORS))
            tint.setAlpha(
                random.randint(45, 130) if spike else random.randint(6, 16)
            )
            painter.fillRect(0, y, width, band, tint)

    def _paint_slices(
        self, painter: QPainter, width: int, height: int, spike: bool
    ) -> None:
        count = random.randint(14, 30) if spike else random.randint(1, 4)
        for _ in range(count):
            y = random.randint(0, height - 1)
            slice_height = (
                random.randint(1, 22) if spike else random.randint(1, 2)
            )
            slice_width = random.randint(
                width // 12, max(width // 12 + 1, width // 2)
            )
            x = random.randint(0, max(0, width - slice_width))
            color = QColor(random.choice(_COLORS))
            color.setAlpha(
                random.randint(50, 180) if spike else random.randint(8, 26)
            )
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
        self, painter: QPainter, width: int, height: int, spike: bool
    ) -> None:
        alpha = random.randint(18, 60) if spike else random.randint(4, 9)
        painter.setPen(QPen(QColor(57, 255, 106, alpha)))
        step = random.choice((2, 3)) if spike else 3
        for y in range(0, height, step):
            painter.drawLine(0, y, width, y)

    def _paint_noise(
        self, painter: QPainter, width: int, height: int, spike: bool
    ) -> None:
        base = max(18, min(80, width * height // 60000))
        count = random.randint(base * 8, base * 14) if spike else random.randint(
            base // 2, base
        )
        count = min(count, 1300)
        for _ in range(count):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            size = random.randint(1, 3) if spike else 1
            fleck = QColor(random.choice(_NOISE))
            fleck.setAlpha(
                random.randint(70, 220) if spike else random.randint(20, 65)
            )
            painter.fillRect(x, y, size, size, fleck)

    def _paint_bars(
        self, painter: QPainter, width: int, height: int, spike: bool
    ) -> None:
        chance = 0.7 if spike else 0.04
        if random.random() >= chance:
            return
        y = random.randint(0, height - 1)
        bar = random.randint(1, 8) if spike else 1
        main = QColor(random.choice(_COLORS[:3]))
        main.setAlpha(210 if spike else 60)
        painter.fillRect(0, y, width, bar, main)
        fringe = QColor(random.choice(_COLORS[:3]))
        fringe.setAlpha(120 if spike else 35)
        painter.fillRect(0, y + bar, width, 1, fringe)
        painter.fillRect(0, max(0, y - 1), width, 1, fringe)

        if spike and random.random() < 0.4:
            x = random.randint(0, width - 1)
            column = random.randint(1, 5)
            col = QColor(random.choice(_COLORS[:3]))
            col.setAlpha(random.randint(60, 150))
            painter.fillRect(x, 0, column, height, col)

    def _paint_spike_blocks(
        self, painter: QPainter, width: int, height: int
    ) -> None:
        for _ in range(random.randint(1, 4)):
            block_width = random.randint(width // 12, width // 3)
            block_height = random.randint(8, max(9, height // 6))
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            color = QColor(random.choice(_NOISE))
            color.setAlpha(random.randint(15, 60))
            painter.fillRect(x, y, block_width, block_height, color)


class GlitchManager(QObject):
    """Keeps one glitch overlay alive on every connected screen."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._overlays: dict[QScreen, GlitchOverlay] = {}

        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(self._add_screen)
            app.screenRemoved.connect(self._remove_screen)
        for screen in QGuiApplication.screens():
            self._add_screen(screen)

    def _add_screen(self, screen: QScreen) -> None:
        if screen in self._overlays:
            return
        overlay = GlitchOverlay(screen)
        overlay.show()
        self._overlays[screen] = overlay

    def _remove_screen(self, screen: QScreen) -> None:
        overlay = self._overlays.pop(screen, None)
        if overlay is not None:
            overlay.close()
            overlay.deleteLater()

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
