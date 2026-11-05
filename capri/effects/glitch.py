from __future__ import annotations
from capri.ui.fonts import get_hud_font

import math
import random

from PySide6.QtCore import QElapsedTimer, QObject, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen, QScreen
from PySide6.QtWidgets import QWidget

from .glitch_paint import paint_frame
from .transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
    PIXEL_SIZE,
    pick_palette_color,
    snap_pixel,
    with_alpha,
)
from ..ui.speech_sfx import get_speech_sfx

_BASE_INTERVAL_MS = 80

class GlitchBurstOverlay(QWidget):
    

    finished = Signal()

    def __init__(
        self,
        rect: QRect,
        duration_ms: int = 1400,
        intensity: str = "strong",
        parent: QWidget | None = None,
    ) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(parent, flags)
        self.setWindowTitle("Глитч окна Capri")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._intensity = intensity
        self._target_rect = rect
        self.setGeometry(rect)

        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(24)
        self._frame_timer.timeout.connect(self._tick)

        self._clock = QElapsedTimer()
        self._duration_ms = duration_ms

    def showEvent(self, event) -> None:
        super().showEvent(event)
        wh = self.windowHandle()
        if wh is not None:
            for scr in QGuiApplication.screens():
                if scr.geometry().intersects(self._target_rect):
                    wh.setScreen(scr)
                    break
        self.setGeometry(self._target_rect)

    def start(self) -> None:
        self.show()
        self.raise_()
        self._clock.start()
        self._frame_timer.start()
        try:
            get_speech_sfx().play_lightning_strike()
        except Exception:
            pass

    def _tick(self) -> None:
        elapsed = self._clock.elapsed()
        if elapsed >= self._duration_ms:
            self._frame_timer.stop()
            self.finished.emit()
            self.close()
            self.deleteLater()
            return
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            painter.end()
            return

        elapsed = self._clock.elapsed() if self._clock.isValid() else 0
        progress = min(1.0, elapsed / max(1, self._duration_ms))

        alpha = int(45 + 35 * math.sin(progress * math.pi * 3))
        bg_color = QColor(COLOR_OBSIDIAN)
        bg_color.setAlpha(alpha)
        painter.fillRect(0, 0, w, h, bg_color)

        frame_alpha = int(180 + 75 * math.sin(progress * math.pi * 6))
        frame_color = QColor(COLOR_CRIMSON if random.random() < 0.75 else COLOR_ACID_GREEN)
        frame_color.setAlpha(min(255, max(0, frame_alpha)))
        bw = PIXEL_SIZE * 2
        painter.fillRect(0, 0, w, bw, frame_color)
        painter.fillRect(0, h - bw, w, bw, frame_color)
        painter.fillRect(0, 0, bw, h, frame_color)
        painter.fillRect(w - bw, 0, bw, h, frame_color)

        slice_count = random.randint(4, 9)
        for _ in range(slice_count):
            sy = snap_pixel(random.randint(0, max(0, h - 1)))
            sh = PIXEL_SIZE * random.randint(1, 4)
            sw = snap_pixel(random.randint(w // 4, w))
            sx = snap_pixel(random.randint(0, max(0, w - sw)))
            scolor = QColor(pick_palette_color())
            scolor.setAlpha(random.randint(110, 220))
            painter.fillRect(sx, sy, sw, sh, scolor)

            if random.random() < 0.8:
                offset = random.choice((-20, -12, 12, 20))
                ghost_color = QColor(COLOR_ELECTRIC_BLUE if offset > 0 else COLOR_CRIMSON)
                ghost_color.setAlpha(random.randint(90, 180))
                painter.fillRect(max(0, min(w - sw, sx + offset)), sy, sw // 2, sh, ghost_color)

        paint_frame(painter, w, h, intensity="strong")

        if 0.15 <= progress <= 0.85:
            banner_w = min(w - 40, max(260, w // 2))
            banner_h = 36
            bx = (w - banner_w) // 2
            by = (h - banner_h) // 2
            painter.fillRect(bx, by, banner_w, banner_h, with_alpha(COLOR_OBSIDIAN, 220))
            painter.fillRect(bx, by, banner_w, 2, COLOR_CRIMSON)
            painter.fillRect(bx, by + banner_h - 2, banner_w, 2, COLOR_ACID_GREEN)

            font = get_hud_font(12, bold=True)
            painter.setFont(font)
            painter.setPen(COLOR_CRIMSON if random.random() < 0.6 else COLOR_WHITE)
            hud_text = random.choice((
                "⚠ CAPRI::BREACH_PROTOCOL",
                "⚡ RELIC 2.0 OVERRIDE",
                "▶ KIROSHI INTERCEPTION",
                "SYSTEM::ALERT // 0xDEAD",
            ))
            painter.drawText(bx + 12, by + 23, hud_text)

        painter.end()

class GlitchOverlay(QWidget):

    amplitude_changed = Signal(float)

    def __init__(self, screen: QScreen, intensity: str = "weak") -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(None, flags)
        self._screen = screen
        self._intensity = intensity
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
        self._update_timer_interval()
        self._frame_timer.timeout.connect(self._tick)
        self._frame_timer.start()

    def set_intensity(self, intensity: str) -> None:
        if intensity not in ("weak", "medium", "strong"):
            intensity = "weak"
        if self._intensity == intensity:
            return
        self._intensity = intensity
        self._update_timer_interval()
        self.update()

    def _update_timer_interval(self) -> None:
        if self._intensity == "strong":
            interval = 50
        elif self._intensity == "medium":
            interval = 65
        else:
            interval = 80
        self._frame_timer.setInterval(interval)

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

    def showEvent(self, event) -> None:
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

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        if self.width() > 0 and self.height() > 0:
            paint_frame(painter, self.width(), self.height(), self._intensity)
        painter.end()

class GlitchManager(QObject):

    amplitude_changed = Signal(float)

    def __init__(
        self, parent: QObject | None = None, intensity: str = "weak"
    ) -> None:
        super().__init__(parent)
        self._overlays: dict[QScreen, GlitchOverlay] = {}
        self._amplitudes: dict[QScreen, float] = {}
        self._enabled = True
        self._intensity = (
            intensity if intensity in ("weak", "medium", "strong") else "weak"
        )

        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(self._add_screen)
            app.screenRemoved.connect(self._remove_screen)
        for screen in QGuiApplication.screens():
            self._add_screen(screen)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def intensity(self) -> str:
        return self._intensity

    def set_intensity(self, intensity: str) -> None:
        if intensity not in ("weak", "medium", "strong"):
            intensity = "weak"
        if self._intensity == intensity:
            return
        self._intensity = intensity
        for overlay in self._overlays.values():
            overlay.set_intensity(intensity)

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
        overlay = GlitchOverlay(screen, intensity=self._intensity)
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
