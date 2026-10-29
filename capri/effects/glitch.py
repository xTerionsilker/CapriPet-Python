from __future__ import annotations

import random

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QPainter, QScreen
from PySide6.QtWidgets import QWidget

from .glitch_paint import paint_frame

_BASE_INTERVAL_MS = 80


class GlitchOverlay(QWidget):

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
        self.setWindowTitle("Глитч-оверлей Capri")
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

    def set_active(self, active: bool) -> None:
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

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        wh = self.windowHandle()
        if wh is not None:
            wh.setScreen(self._screen)

    def _sync_geometry(self, *_args) -> None:
        self.setGeometry(self._screen.geometry())
        wh = self.windowHandle()
        if wh is not None:
            wh.setScreen(self._screen)

    def _tick(self) -> None:
        self._update_amplitude()
        self.update()

    def _update_amplitude(self) -> None:
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

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        if self.width() > 0 and self.height() > 0:
            paint_frame(painter, self.width(), self.height())
        painter.end()


class GlitchManager(QObject):

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
        if enabled == self._enabled:
            return
        self._enabled = enabled
        for overlay in self._overlays.values():
            overlay.set_active(enabled)

    def toggle(self) -> bool:
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
