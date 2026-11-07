from __future__ import annotations
from capri.ui.theme import get_hud_font
from capri.ui.speech_sfx import get_speech_sfx

import math
import random

from PySide6.QtCore import QElapsedTimer, QObject, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen, QScreen
from PySide6.QtWidgets import QWidget

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

_BASE_INTERVAL_MS = 80

_HUD_MICRO_TAGS = (
    "RELIC_2.0 // SYNC",
    "KIROSHI_OPTICS // OK",
    "BUFFER_OVRFLW [0x7F]",
    "NET_PULSE // 0.18ms",
    "DAEMON_PROT // ACTIVE",
    "MEM_CORRUPT: 0x3F",
    "NEURAL_LINK :: 99.4%",
    "TRACE_ROUTE // ICE",
)

def paint_frame(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    painter.fillRect(0, 0, width, height, Qt.GlobalColor.transparent)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    paint_scanlines(painter, width, height, intensity)
    paint_kiroshi_brackets(painter, width, height, intensity)
    paint_slices(painter, width, height, intensity)
    paint_tears(painter, width, height, intensity)
    paint_circuit_traces(painter, width, height, intensity)
    paint_cyber_markers(painter, width, height, intensity)
    paint_subtle_noise(painter, width, height, intensity)

def paint_scanlines(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    pen_color = QColor(COLOR_OBSIDIAN)
    if intensity == "strong":
        pen_color.setAlpha(random.randint(12, 22))
        step = PIXEL_SIZE
    elif intensity == "medium":
        pen_color.setAlpha(random.randint(8, 16))
        step = PIXEL_SIZE * 2
    else:
        pen_color.setAlpha(random.randint(6, 12))
        step = PIXEL_SIZE * 2

    painter.setPen(QPen(pen_color, 1))
    for y in range(0, height, step):
        painter.drawLine(0, y, width, y)

def paint_tears(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    chance = 0.40 if intensity == "strong" else (0.28 if intensity == "medium" else 0.18)
    if random.random() >= chance:
        return

    count = random.randint(1, 2) if intensity == "strong" else 1
    for _ in range(count):
        y = snap_pixel(random.randint(0, max(0, height - 1)))
        band = random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)) if intensity == "strong" else PIXEL_SIZE
        tint = QColor(pick_palette_color())
        alpha_range = (
            (16, 35) if intensity == "strong" else ((12, 25) if intensity == "medium" else (8, 18))
        )
        tint.setAlpha(random.randint(*alpha_range))
        painter.fillRect(0, y, width, band, tint)

def paint_slices(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    chance = 0.65 if intensity == "strong" else (0.50 if intensity == "medium" else 0.40)
    if random.random() >= chance:
        return

    if intensity == "strong":
        count = random.randint(2, 4)
    elif intensity == "medium":
        count = random.randint(1, 3)
    else:
        count = random.randint(1, 2)

    for _ in range(count):
        y = snap_pixel(random.randint(0, max(0, height - 1)))
        slice_height = (
            random.choice((PIXEL_SIZE, PIXEL_SIZE * 2))
            if intensity == "strong"
            else PIXEL_SIZE
        )
        max_div = 3 if intensity == "strong" else 4
        slice_width = snap_pixel(
            random.randint(width // 15, max(width // 15 + 1, width // max_div))
        )
        x = snap_pixel(random.randint(0, max(0, width - slice_width)))

        color = QColor(pick_palette_color())
        alpha_range = (
            (24, 48) if intensity == "strong" else ((20, 38) if intensity == "medium" else (16, 32))
        )
        color.setAlpha(random.randint(*alpha_range))
        painter.fillRect(x, y, slice_width, slice_height, color)

        ghost_chance = 0.85 if intensity == "strong" else 0.65
        if random.random() < ghost_chance:
            ghost_color = QColor(
                COLOR_CRIMSON if random.random() < 0.75 else COLOR_ELECTRIC_BLUE
            )
            ghost_color.setAlpha(random.randint(10, 24))
            ghost_offset = random.choice((-24, -16, -8, 8, 16, 24)) if intensity == "strong" else random.choice((-16, -8, 8, 16))
            gx = max(0, min(width - 1, x + ghost_offset))
            gw = min(slice_width // 2, width - gx)
            if gw > 0:
                painter.fillRect(gx, y, gw, slice_height, ghost_color)

def paint_circuit_traces(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    chance = 0.35 if intensity == "strong" else (0.24 if intensity == "medium" else 0.15)
    if random.random() >= chance:
        return

    y = snap_pixel(random.randint(height // 10, max(height // 10 + 1, height - height // 10)))
    x1 = snap_pixel(random.randint(0, max(0, width - width // 3)))
    w = snap_pixel(random.randint(width // 8, width // 3))

    color = QColor(COLOR_ACID_GREEN if random.random() < 0.65 else COLOR_CRIMSON)
    alpha_range = (
        (30, 55) if intensity == "strong" else ((25, 45) if intensity == "medium" else (20, 38))
    )
    color.setAlpha(random.randint(*alpha_range))
    painter.fillRect(x1, y, w, PIXEL_SIZE, color)

    if random.random() < 0.6:
        bend_len = PIXEL_SIZE * random.randint(3, 7)
        dir_y = 1 if (y + bend_len < height) else -1
        painter.fillRect(x1 + w - PIXEL_SIZE, y, PIXEL_SIZE, bend_len * dir_y, color)

        node_y = y + (bend_len * dir_y)
        painter.fillRect(x1 + w - PIXEL_SIZE * 2, node_y, PIXEL_SIZE * 3, PIXEL_SIZE, color)
    else:
        painter.fillRect(x1 + w, y - PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 3, color)

def paint_kiroshi_brackets(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    chance = 0.28 if intensity == "strong" else (0.18 if intensity == "medium" else 0.12)
    if random.random() >= chance:
        return

    if random.random() < 0.6:
        margin = 32
        corner = random.choice(((margin, margin), (width - margin - 40, margin),
                               (margin, height - margin - 40), (width - margin - 40, height - margin - 40)))
        bx, by = corner
    else:
        bx = snap_pixel(random.randint(width // 8, max(width // 8 + 1, width - width // 4)))
        by = snap_pixel(random.randint(height // 8, max(height // 8 + 1, height - height // 4)))

    size = PIXEL_SIZE * random.randint(3, 5)
    bracket_color = QColor(COLOR_CRIMSON if random.random() < 0.75 else COLOR_ACID_GREEN)
    alpha_range = (
        (35, 60) if intensity == "strong" else ((28, 50) if intensity == "medium" else (22, 45))
    )
    bracket_color.setAlpha(random.randint(*alpha_range))

    painter.fillRect(bx, by, size, PIXEL_SIZE, bracket_color)
    painter.fillRect(bx, by, PIXEL_SIZE, size, bracket_color)

    dot_color = QColor(COLOR_WHITE)
    dot_color.setAlpha(random.randint(25, 50))
    painter.fillRect(bx + size + PIXEL_SIZE, by + PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE, dot_color)

def paint_cyber_markers(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    chance = 0.20 if intensity == "strong" else (0.13 if intensity == "medium" else 0.08)
    if random.random() >= chance:
        return

    x = snap_pixel(random.randint(width // 10, max(width // 10 + 1, width - width // 3)))
    y = snap_pixel(random.randint(height // 10, max(height // 10 + 1, height - height // 10)))

    tag = random.choice(_HUD_MICRO_TAGS)
    font = get_hud_font(9, bold=True)
    painter.setFont(font)

    text_color = QColor(COLOR_CRIMSON if random.random() < 0.70 else COLOR_ACID_GREEN)
    alpha_range = (
        (45, 75) if intensity == "strong" else ((35, 65) if intensity == "medium" else (30, 55))
    )
    text_color.setAlpha(random.randint(*alpha_range))
    painter.setPen(text_color)
    painter.drawText(x, y, tag)

    bar_w = PIXEL_SIZE * random.randint(4, 10)
    painter.fillRect(x, y + 3, bar_w, 2, text_color)

def paint_subtle_noise(
    painter: QPainter, width: int, height: int, intensity: str = "weak"
) -> None:
    if intensity == "strong":
        count = random.randint(20, 50)
        alpha_range = (25, 65)
    elif intensity == "medium":
        count = random.randint(12, 30)
        alpha_range = (20, 50)
    else:
        count = random.randint(6, 18)
        alpha_range = (15, 45)

    for _ in range(count):
        x = snap_pixel(random.randint(0, max(0, width - 1)))
        y = snap_pixel(random.randint(0, max(0, height - 1)))
        fleck = QColor(pick_palette_color())
        fleck.setAlpha(random.randint(*alpha_range))
        painter.fillRect(x, y, PIXEL_SIZE, PIXEL_SIZE, fleck)


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
