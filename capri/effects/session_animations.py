from __future__ import annotations

import math
import random
from typing import Callable

from PySide6.QtCore import QElapsedTimer, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from .transition_fx import (
    BAYER_4X4,
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    PIXEL_SIZE,
    CyberHoloReticle,
    CyberPixelSpark,
    CyberShockwaveRing,
    pick_palette_color,
    snap_pixel,
)
from ..ui.speech_sfx import get_speech_sfx

# Длительность сессионной анимации. Действие выполняется после её завершения.
SESSION_ANIMATION_DURATION_MS = 1500
SESSION_ACTION_LEAD_MS = 1800

_GLITCH_GLYPHS = "01#@%&$/\\<>[]{}§¤¦"
_GLITCH_PHRASES = (
    "0xDEADBEEF",
    "MEMORY//CORRUPT",
    "SIGNAL_LOST",
    "CARRIER_ERR",
    "PACKET_DESYNC",
    "CRC_FAIL:0x7F",
    "NULL_POINTER",
    "SEGFAULT",
    "DATA_BUS//NOISE",
    "CAPRI.CORE::PANIC",
)

_ACTION_PROFILES: dict[str, dict[str, object]] = {
    "lock": {
        "title": "SCREEN//LOCK",
        "subtitle": "SECURING PERIMETER",
        "accent": COLOR_CRIMSON,
        "counter": COLOR_ACID_GREEN,
    },
    "power_off": {
        "title": "POWER//DOWN",
        "subtitle": "CORE SHUTDOWN SEQUENCE",
        "accent": COLOR_CRIMSON,
        "counter": COLOR_WHITE,
    },
    "suspend": {
        "title": "CRYO//SUSPEND",
        "subtitle": "ENTERING LOW-POWER STASIS",
        "accent": COLOR_ELECTRIC_BLUE,
        "counter": COLOR_VIOLET,
    },
    "reboot": {
        "title": "KERNEL//RESTART",
        "subtitle": "REINITIALIZING CORE",
        "accent": COLOR_ACID_GREEN,
        "counter": COLOR_CRIMSON,
    },
}


def _font(size: int) -> QFont:
    font = QFont("Press Start 2P")
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(size)
    font.setBold(True)
    return font


def _with_alpha(color: QColor, alpha: int) -> QColor:
    result = QColor(color)
    result.setAlpha(max(0, min(255, int(alpha))))
    return result


class SessionAnimationOverlay(QWidget):
    """Киберпанк-анимация Капри перед системными действиями сессии."""

    finished = Signal()

    def __init__(
        self,
        screen_rect: QRect,
        window_rect: QRect,
        action: str,
        target: QWidget | None = None,
        parent: QWidget | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(parent, flags)
        self._screen_rect = QRect(screen_rect)
        self._window_rect = QRect(window_rect)
        self._action = action if action in _ACTION_PROFILES else "lock"
        self._profile = _ACTION_PROFILES[self._action]
        self._target = target
        self._on_finished = on_finished

        self._target_pixmap: QPixmap | None = None
        if target is not None and target.width() > 0 and target.height() > 0:
            try:
                self._target_pixmap = target.grab()
            except Exception:
                self._target_pixmap = None

        self._clock: QElapsedTimer | None = None
        self._last_elapsed = 0
        self._progress = 0.0
        self._finished = False
        self._peak_sound_played = False
        self._particles: list[CyberPixelSpark] = []
        self._frame = 0
        self._glitch_seed = 0
        self._burst_until = 0.0
        self._next_burst_at = 0.0
        self._glitch_sounds_left = 2

        self.setWindowTitle("Сессионная анимация Capri")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(self._screen_rect)

        offset = self._screen_rect.topLeft()
        self._local_window = self._window_rect.translated(-offset)

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._clock = QElapsedTimer()
        self._clock.start()
        self._last_elapsed = 0
        self._next_burst_at = random.uniform(0.08, 0.18)
        self._glitch_seed = random.randrange(0, 0xFFFF)
        self._spawn_ambient_particles(40)
        self.raise_()
        self.show()
        self._timer.start()
        try:
            get_speech_sfx().play_session_action(self._action)
        except Exception:
            pass

    def _tick(self) -> None:
        if self._clock is None:
            return
        elapsed = self._clock.elapsed()
        dt = max(0.001, (elapsed - self._last_elapsed) / 1000.0)
        self._last_elapsed = elapsed
        self._progress = min(1.0, elapsed / SESSION_ANIMATION_DURATION_MS)
        p = self._progress
        self._frame += 1
        self._update_glitch_bursts(p)

        if p >= 0.46 and not self._peak_sound_played:
            self._peak_sound_played = True
            try:
                sfx = get_speech_sfx()
                if self._action == "reboot":
                    sfx.play_lightning_zap()
                elif self._action == "power_off":
                    sfx.play_lightning_strike()
                elif self._action == "lock":
                    sfx.play_lightning_arc()
            except Exception:
                pass

        self._spawn_action_particles(p, dt)
        self._particles = [particle for particle in self._particles if particle.step(dt)]
        self.update()

        if p >= 1.0:
            self._finish()

    def _update_glitch_bursts(self, p: float) -> None:
        if p >= 0.94:
            self._burst_until = 1.0
            return
        if p < self._next_burst_at:
            return

        power = self._glitch_power(p)
        duration = random.uniform(0.06, 0.15) * (0.8 + power * 0.9)
        self._burst_until = min(0.95, p + duration)
        interval = random.uniform(0.10, 0.24) / (0.75 + power * 0.8)
        self._next_burst_at = p + interval
        self._glitch_seed = random.randrange(0, 0xFFFF)

        if self._glitch_sounds_left > 0 and p > 0.22:
            self._glitch_sounds_left -= 1
            try:
                get_speech_sfx().play_lightning_zap()
            except Exception:
                pass

    @staticmethod
    def _glitch_power(p: float) -> float:
        """Интенсивность глюков: растёт от 0.2 до 2.0 к концу анимации."""
        t = max(0.0, min(1.0, (p - 0.12) / 0.88))
        return 0.2 + 1.8 * (t ** 1.6)

    def _is_glitch_burst(self, p: float) -> bool:
        return p <= self._burst_until

    @staticmethod
    def _corrupt_text(text: str, probability: float) -> str:
        if probability <= 0.0:
            return text
        return "".join(
            random.choice(_GLITCH_GLYPHS) if random.random() < probability else char
            for char in text
        )

    def _finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._timer.stop()
        self.finished.emit()
        if self._on_finished is not None:
            try:
                self._on_finished()
            except Exception:
                pass
        self.close()

    def _spawn_ambient_particles(self, count: int) -> None:
        wr = self._local_window
        if wr.width() <= 0 or wr.height() <= 0:
            return
        for _ in range(count):
            x = wr.center().x() + random.randint(-wr.width(), wr.width())
            y = wr.center().y() + random.randint(-wr.height(), wr.height())
            speed = random.uniform(30.0, 180.0)
            angle = random.uniform(0.0, math.tau)
            self._particles.append(
                CyberPixelSpark(
                    snap_pixel(x),
                    snap_pixel(y),
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    color=pick_palette_color(),
                    size=random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)),
                    life=random.uniform(0.30, 0.80),
                    kind=random.choice(("spark", "bit", "bar")),
                )
            )

    def _spawn_action_particles(self, p: float, dt: float) -> None:
        if p > 0.92:
            return
        wr = self._local_window
        if wr.width() <= 0 or wr.height() <= 0:
            return
        rate = 6.0 if self._action in ("power_off", "reboot") else 3.5
        rate *= 0.65 + self._glitch_power(p)
        if random.random() > rate * dt:
            return
        accent: QColor = self._profile["accent"]  # type: ignore[assignment]
        for _ in range(2):
            x = wr.center().x() + random.randint(-wr.width() // 2, wr.width() // 2)
            y = wr.center().y() + random.randint(-wr.height() // 2, wr.height() // 2)
            if self._action == "power_off":
                vx = random.uniform(-40.0, 40.0)
                vy = random.uniform(90.0, 260.0)
            elif self._action == "reboot":
                angle = random.uniform(0.0, math.tau)
                speed = random.uniform(90.0, 260.0)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
            elif self._action == "suspend":
                vx = random.uniform(-18.0, 18.0)
                vy = random.uniform(-70.0, -25.0)
            else:
                vx = random.choice((-1.0, 1.0)) * random.uniform(80.0, 220.0)
                vy = random.uniform(-30.0, 30.0)
            self._particles.append(
                CyberPixelSpark(
                    snap_pixel(x),
                    snap_pixel(y),
                    vx,
                    vy,
                    color=accent if random.random() < 0.65 else pick_palette_color(),
                    size=random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)),
                    life=random.uniform(0.25, 0.60),
                    kind=random.choice(("spark", "bit", "bar")),
                )
            )

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p = self._progress
        accent: QColor = self._profile["accent"]  # type: ignore[assignment]
        counter: QColor = self._profile["counter"]  # type: ignore[assignment]

        backdrop = 110 + 45 * math.sin(p * math.pi) + 120 * (p ** 2)
        painter.fillRect(self.rect(), _with_alpha(COLOR_OBSIDIAN, int(backdrop)))

        self._paint_scanlines(painter, accent, p)
        self._paint_target(painter, p, accent, counter)
        self._paint_screen_glitches(painter, p, accent, counter)
        self._paint_hud(painter, p, accent, counter)
        self._paint_action_glyph(painter, p, accent, counter)

        for particle in self._particles:
            particle.draw(painter)

        if 0.10 <= p <= 0.88:
            flash_p = (p - 0.10) / 0.78
            self._paint_flash(painter, flash_p, accent, counter)

        self._paint_screen_takeover(painter, p, accent, counter)
        painter.end()

    def _paint_scanlines(self, painter: QPainter, accent: QColor, p: float) -> None:
        alpha = int(38 + 28 * math.sin(p * math.pi * 6.0))
        painter.setPen(QPen(_with_alpha(COLOR_OBSIDIAN, alpha), 2))
        for y in range(0, self.height(), PIXEL_SIZE):
            painter.drawLine(0, y, self.width(), y)

        sweep_y = snap_pixel(int(self.height() * min(1.0, p * 1.15)))
        painter.fillRect(0, sweep_y, self.width(), PIXEL_SIZE * 2, _with_alpha(accent, 95))
        painter.fillRect(0, sweep_y - PIXEL_SIZE * 2, self.width(), PIXEL_SIZE * 2, _with_alpha(COLOR_WHITE, 28))

        if self._is_glitch_burst(p):
            power = self._glitch_power(p)
            for _ in range(1 + int(power)):
                roll_y = snap_pixel(random.randint(0, max(0, self.height() - PIXEL_SIZE * 12)))
                roll_h = random.choice(
                    (PIXEL_SIZE * 4, PIXEL_SIZE * 8, PIXEL_SIZE * 16, PIXEL_SIZE * 32)
                )
                painter.fillRect(
                    0,
                    roll_y,
                    self.width(),
                    roll_h,
                    _with_alpha(COLOR_OBSIDIAN, random.randint(80, min(245, int(90 + 80 * power)))),
                )
                painter.fillRect(
                    0,
                    roll_y + roll_h,
                    self.width(),
                    PIXEL_SIZE,
                    _with_alpha(COLOR_ACID_GREEN, random.randint(40, min(240, int(70 + 75 * power)))),
                )

    def _paint_screen_glitches(
        self,
        painter: QPainter,
        p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:
        burst = self._is_glitch_burst(p)
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        rng = random.Random(self._glitch_seed + self._frame * 37)
        wr = self._local_window
        power = self._glitch_power(p)

        # Горизонтальные разрывы кадра и хроматические сдвиги.
        tear_count = (rng.randint(5, 13) if burst else rng.randint(0, 2)) * max(1, int(power))
        for _ in range(tear_count):
            y = snap_pixel(rng.randint(0, max(0, h - 1)))
            tear_h = rng.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 4, PIXEL_SIZE * 8))
            x = snap_pixel(rng.randint(-w // 5, w))
            tear_w = snap_pixel(rng.randint(w // 12, max(w // 12 + 1, w // 2)))
            color = pick_palette_color()
            painter.fillRect(
                x,
                y,
                tear_w,
                tear_h,
                _with_alpha(color, rng.randint(55, min(255, int(85 + 90 * power)))),
            )

        if burst:
            for _ in range(max(3, int(2 + power * 3))):
                y = snap_pixel(rng.randint(0, max(0, h - PIXEL_SIZE * 6)))
                band_h = rng.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 4))
                shift = rng.choice((-PIXEL_SIZE * 8, -PIXEL_SIZE * 4, -PIXEL_SIZE * 2, PIXEL_SIZE * 2, PIXEL_SIZE * 4, PIXEL_SIZE * 8))
                painter.fillRect(shift, y, w, band_h, _with_alpha(COLOR_CRIMSON, min(230, int(45 + 55 * power))))
                painter.fillRect(-shift, y + PIXEL_SIZE, w, band_h, _with_alpha(COLOR_ACID_GREEN, min(220, int(35 + 45 * power))))

        # Датамош-блоки, вырванные из спрайта Капри.
        if burst and self._target_pixmap is not None and not self._target_pixmap.isNull():
            pw = self._target_pixmap.width()
            ph = self._target_pixmap.height()
            for _ in range(int(rng.randint(5, 12) * (0.7 + power * 0.75))):
                bw = snap_pixel(rng.randint(PIXEL_SIZE * 4, max(PIXEL_SIZE * 5, wr.width() // 2)))
                bh = snap_pixel(rng.randint(PIXEL_SIZE * 2, max(PIXEL_SIZE * 3, wr.height() // 4)))
                sx = snap_pixel(rng.randint(0, max(0, pw - bw)))
                sy = snap_pixel(rng.randint(0, max(0, ph - bh)))
                dx = snap_pixel(wr.left() + rng.randint(-wr.width() * (1 + int(power)), wr.width() * (1 + int(power))))
                dy = snap_pixel(wr.top() + rng.randint(-wr.height() * (1 + int(power)), wr.height() * (1 + int(power))))
                src = QRect(sx, sy, min(bw, pw - sx), min(bh, ph - sy))
                if src.width() <= 0 or src.height() <= 0:
                    continue
                painter.drawPixmap(QRect(dx, dy, src.width(), src.height()), self._target_pixmap, src)
                painter.fillRect(
                    QRect(dx, dy, src.width(), src.height()),
                    _with_alpha(
                        rng.choice((COLOR_CRIMSON, COLOR_ACID_GREEN, COLOR_ELECTRIC_BLUE, COLOR_VIOLET)),
                        rng.randint(28, min(210, int(45 + 65 * power))),
                    ),
                )

        # Плотный цифровой шум и битые пиксельные кластеры.
        noise_base = rng.randint(45, 150) if burst else rng.randint(6, 18)
        noise_count = int(noise_base * (0.65 + power * 0.9))
        for _ in range(noise_count):
            nx = snap_pixel(rng.randint(0, max(0, w - 1)))
            ny = snap_pixel(rng.randint(0, max(0, h - 1)))
            size = rng.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 4, PIXEL_SIZE * 8))
            painter.fillRect(
                nx,
                ny,
                size,
                size,
                _with_alpha(pick_palette_color(), rng.randint(70, min(255, int(150 + 65 * power)))),
            )

        # Аварийная телеметрия в случайных местах экрана.
        if burst and rng.random() < min(0.98, 0.55 + 0.2 * power):
            phrase = rng.choice(_GLITCH_PHRASES)
            painter.setFont(_font(rng.choice((8, 10, 12, 16))))
            tx = snap_pixel(rng.randint(20, max(21, w - 420)))
            ty = snap_pixel(rng.randint(30, max(31, h - 30)))
            shift = rng.choice((PIXEL_SIZE, PIXEL_SIZE * 2))
            painter.setPen(_with_alpha(COLOR_CRIMSON, rng.randint(150, 240)))
            painter.drawText(tx - shift, ty, phrase)
            painter.setPen(_with_alpha(COLOR_ACID_GREEN, rng.randint(120, 210)))
            painter.drawText(tx + shift, ty, phrase)
            painter.setPen(_with_alpha(COLOR_WHITE, rng.randint(180, 255)))
            painter.drawText(tx, ty, phrase)

        # Аварийные боковые шины и обсидиановые вырезы.
        if burst:
            edge_h = snap_pixel(rng.randint(PIXEL_SIZE * 8, max(PIXEL_SIZE * 9, h // 8)))
            edge_y = snap_pixel(rng.randint(0, max(0, h - edge_h)))
            painter.fillRect(0, edge_y, rng.choice((PIXEL_SIZE * 2, PIXEL_SIZE * 4)), edge_h, _with_alpha(accent, rng.randint(100, 220)))
            painter.fillRect(w - PIXEL_SIZE * 3, edge_y, PIXEL_SIZE * 3, edge_h, _with_alpha(counter, rng.randint(90, 190)))
            if rng.random() < 0.55:
                cut_y = snap_pixel(rng.randint(0, max(0, h - PIXEL_SIZE * 8)))
                painter.fillRect(0, cut_y, w, rng.choice((PIXEL_SIZE * 2, PIXEL_SIZE * 4)), _with_alpha(COLOR_OBSIDIAN, rng.randint(150, 245)))

    def _paint_screen_takeover(
        self,
        painter: QPainter,
        p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:
        """К финалу глюки разрастаются в сплошную пиксельную мозаику."""
        if p < 0.58:
            return

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        coverage = max(0.0, min(1.0, (p - 0.58) / 0.37))
        cell = PIXEL_SIZE * 4
        colors = (
            accent,
            counter,
            COLOR_CRIMSON,
            COLOR_ACID_GREEN,
            COLOR_WHITE,
            COLOR_ELECTRIC_BLUE,
            COLOR_VIOLET,
            COLOR_OBSIDIAN,
        )
        seed = (self._glitch_seed * 83492791) ^ (self._frame * 2654435761)
        alpha = int(90 + 165 * coverage)

        for y in range(0, h, cell):
            for x in range(0, w, cell):
                hash_value = (
                    (x * 73856093) ^ (y * 19349663) ^ seed
                ) & 0xFFFF
                if hash_value / 65535.0 > coverage:
                    continue
                color = colors[hash_value % len(colors)]
                painter.fillRect(
                    x,
                    y,
                    min(cell, w - x),
                    min(cell, h - y),
                    _with_alpha(color, alpha),
                )

        if coverage >= 0.985:
            # Финальная перегрузка: экран полностью уходит в RGB-кашу.
            shift = PIXEL_SIZE * 3
            painter.fillRect(
                self.rect().translated(-shift, 0),
                _with_alpha(COLOR_CRIMSON, 150),
            )
            painter.fillRect(
                self.rect().translated(shift, 0),
                _with_alpha(COLOR_ACID_GREEN, 130),
            )
            painter.setFont(_font(18))
            painter.setPen(_with_alpha(COLOR_WHITE, 230))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                self._corrupt_text("SIGNAL//LOST", 0.35),
            )

    def _paint_target(
        self,
        painter: QPainter,
        p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:
        wr = self._local_window
        if wr.width() <= 0 or wr.height() <= 0:
            return

        painter.save()
        painter.setClipRect(wr.adjusted(-PIXEL_SIZE * 8, -PIXEL_SIZE * 8, PIXEL_SIZE * 8, PIXEL_SIZE * 8))
        self._paint_target_slices(painter, wr, p, accent, counter)
        painter.restore()

        if self._action == "lock":
            offset = int((1.0 - min(1.0, p / 0.65)) * 48)
            CyberHoloReticle.draw(painter, wr, min(1.0, p / 0.55), color=accent, bracket_offset=offset)
        elif self._action == "reboot":
            self._paint_rotation_ring(painter, wr, p, accent, counter)
        elif self._action == "suspend":
            self._paint_stasis_field(painter, wr, p, accent)
        else:
            CyberHoloReticle.draw(painter, wr, max(0.0, 1.0 - p), color=accent)

    def _paint_target_slices(
        self,
        painter: QPainter,
        wr: QRect,
        p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:
        if self._target_pixmap is None or self._target_pixmap.isNull():
            painter.fillRect(wr, _with_alpha(accent, int(35 + 30 * math.sin(p * math.pi))))
            return

        w = wr.width()
        h = wr.height()
        pixmap = self._target_pixmap
        slice_count = 12
        intensity = min(1.0, p / 0.70)

        for i in range(slice_count):
            sy = snap_pixel(i * h / slice_count)
            sh = min(snap_pixel(h / slice_count) + PIXEL_SIZE, h - sy)
            if sh <= 0:
                continue
            y_ratio = (i + 0.5) / slice_count

            if self._action == "lock":
                settle = max(0.0, 1.0 - p / 0.72)
                dx = snap_pixel(random.uniform(-1.0, 1.0) * w * 0.35 * settle)
                dy = 0
            elif self._action == "power_off":
                collapse = max(0.0, (p - 0.35) / 0.65)
                dy = snap_pixel((y_ratio - 0.5) * h * collapse)
                dx = snap_pixel(random.uniform(-1.0, 1.0) * w * 0.10 * (1.0 - collapse))
            elif self._action == "suspend":
                dy = snap_pixel(math.sin(p * math.tau * 2.0 + i * 0.7) * 4.0 * intensity)
                dx = snap_pixel(math.sin(p * math.tau + i * 0.4) * 3.0)
            else:
                scatter = math.sin(p * math.pi)
                angle = (i / slice_count) * math.tau + p * math.tau
                dx = snap_pixel(math.cos(angle) * w * 0.12 * scatter)
                dy = snap_pixel(math.sin(angle) * h * 0.08 * scatter)

            if self._is_glitch_burst(p):
                power = self._glitch_power(p)
                dx += snap_pixel(random.uniform(-1.0, 1.0) * w * 0.22 * power)
                if random.random() < 0.35:
                    dy += snap_pixel(random.uniform(-1.0, 1.0) * h * 0.05 * power)

            src = QRect(0, sy, w, sh)
            dst = QRect(wr.left() + dx, wr.top() + sy + dy, w, sh)
            painter.drawPixmap(dst, pixmap, src)

            if self._is_glitch_burst(p) and random.random() < 0.45:
                ghost_shift = random.choice((-PIXEL_SIZE * 3, -PIXEL_SIZE * 2, PIXEL_SIZE * 2, PIXEL_SIZE * 3))
                painter.setOpacity(0.34)
                painter.drawPixmap(dst.translated(ghost_shift, 0), pixmap, src)
                painter.setOpacity(1.0)
                painter.fillRect(
                    dst.translated(ghost_shift, 0),
                    _with_alpha(
                        COLOR_CRIMSON if ghost_shift < 0 else COLOR_ACID_GREEN,
                        random.randint(35, 75),
                    ),
                )

        if self._action == "suspend":
            tint = _with_alpha(accent, int(75 * intensity))
            painter.fillRect(wr, tint)
        elif self._action == "power_off":
            collapse = max(0.0, (p - 0.50) / 0.50)
            line_h = max(PIXEL_SIZE, snap_pixel(h * (1.0 - collapse)))
            line_rect = QRect(wr.center().x() - w // 2, wr.center().y() - line_h // 2, w, line_h)
            painter.fillRect(line_rect, _with_alpha(COLOR_OBSIDIAN, 235))
            painter.fillRect(line_rect.adjusted(0, line_h // 2 - PIXEL_SIZE, 0, 0), _with_alpha(counter, 220))
        elif self._action == "lock":
            bar_y = wr.top() + snap_pixel((p * 1.3 % 1.0) * h)
            painter.fillRect(wr.left(), bar_y, w, PIXEL_SIZE * 2, _with_alpha(counter, 160))

    def _paint_rotation_ring(
        self,
        painter: QPainter,
        wr: QRect,
        p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:
        radius = max(wr.width(), wr.height()) // 2 + 32
        center = wr.center()
        rect = QRect(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        painter.setPen(QPen(_with_alpha(accent, 220), PIXEL_SIZE * 2))
        start = int(p * 360 * 3)
        for i in range(8):
            painter.drawArc(rect, (start + i * 45) * 16, 22 * 16)
        painter.setPen(QPen(_with_alpha(counter, 180), PIXEL_SIZE))
        inner = rect.adjusted(18, 18, -18, -18)
        for i in range(4):
            painter.drawArc(inner, (-start + i * 90) * 16, 38 * 16)

    def _paint_stasis_field(
        self,
        painter: QPainter,
        wr: QRect,
        p: float,
        accent: QColor,
    ) -> None:
        center = wr.center()
        radius = max(wr.width(), wr.height()) // 2 + 18
        rect = QRect(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        painter.setPen(QPen(_with_alpha(accent, 170), PIXEL_SIZE))
        painter.drawEllipse(rect)
        wave_radius = radius + int(14 * math.sin(p * math.tau * 2.0))
        painter.setPen(QPen(_with_alpha(COLOR_VIOLET, 120), PIXEL_SIZE))
        painter.drawEllipse(rect.adjusted(-8, -8, 8, 8))
        CyberShockwaveRing.draw(painter, center, max(PIXEL_SIZE * 2, wave_radius), _with_alpha(accent, 55))

    def _paint_flash(
        self,
        painter: QPainter,
        flash_p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:
        if flash_p <= 0.18:
            intensity = flash_p / 0.18
        else:
            intensity = max(0.0, 1.0 - (flash_p - 0.18) / 0.82) ** 1.5
        if intensity <= 0.01:
            return

        wr = self._local_window
        shift = PIXEL_SIZE * 2
        alpha = int(150 * intensity)
        painter.fillRect(
            wr.translated(-shift, 0),
            _with_alpha(COLOR_CRIMSON, alpha),
        )
        painter.fillRect(
            wr.translated(shift, 0),
            _with_alpha(COLOR_ACID_GREEN, alpha),
        )
        painter.fillRect(wr, _with_alpha(COLOR_WHITE, int(190 * intensity)))

        center = wr.center()
        radius = snap_pixel(int(max(wr.width(), wr.height()) * 0.9 * flash_p))
        if radius > PIXEL_SIZE * 2:
            CyberShockwaveRing.draw(painter, center, radius, _with_alpha(accent, int(190 * intensity)))
            CyberShockwaveRing.draw(painter, center, max(0, radius - PIXEL_SIZE * 8), _with_alpha(counter, int(130 * intensity)))

        step = PIXEL_SIZE * 2
        zone = wr.adjusted(-PIXEL_SIZE * 24, -PIXEL_SIZE * 24, PIXEL_SIZE * 24, PIXEL_SIZE * 24)
        for y in range(zone.top(), zone.bottom(), step):
            for x in range(zone.left(), zone.right(), step):
                if wr.contains(x, y):
                    continue
                threshold = BAYER_4X4[(y // step) % 4][(x // step) % 4] / 16.0
                if intensity > threshold:
                    painter.fillRect(x, y, step, step, _with_alpha(accent, int(120 * intensity)))

    def _paint_hud(
        self,
        painter: QPainter,
        p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:
        wr = self._local_window
        margin = 22
        hud_width = max(300, min(520, self.width() - margin * 2))
        hud_height = 76
        hud_x = margin
        hud_y = max(margin, wr.top() - hud_height - 20)
        if hud_y < margin:
            hud_y = min(self.height() - hud_height - margin, wr.bottom() + 20)

        burst = self._is_glitch_burst(p)
        jitter_x = random.choice((-6, -4, 0, 0, 4, 6)) if burst else 0
        jitter_y = random.choice((-4, 0, 0, 4)) if burst else 0
        hud = QRect(hud_x + jitter_x, hud_y + jitter_y, hud_width, hud_height)

        painter.fillRect(hud, _with_alpha(COLOR_OBSIDIAN, 225))
        painter.setPen(QPen(_with_alpha(accent, 230), PIXEL_SIZE))
        painter.drawRect(hud)
        if burst:
            painter.setPen(QPen(_with_alpha(counter, random.randint(90, 200)), 1))
            painter.drawRect(hud.adjusted(2, 2, -2, -2))

        title = str(self._profile["title"])
        subtitle = str(self._profile["subtitle"])
        if burst:
            power = self._glitch_power(p)
            title = self._corrupt_text(title, min(0.75, 0.12 + power * 0.22))
            subtitle = self._corrupt_text(subtitle, min(0.55, 0.06 + power * 0.16))

        title_rect = hud.adjusted(14, 12, -14, -40)
        painter.setFont(_font(12))
        if burst:
            painter.setPen(_with_alpha(COLOR_CRIMSON, 220))
            painter.drawText(title_rect.translated(-PIXEL_SIZE, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
            painter.setPen(_with_alpha(COLOR_ACID_GREEN, 200))
            painter.drawText(title_rect.translated(PIXEL_SIZE, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
        painter.setPen(_with_alpha(COLOR_WHITE, 240))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)

        subtitle_rect = hud.adjusted(14, 38, -14, -22)
        painter.setFont(_font(7))
        painter.setPen(_with_alpha(counter, 220))
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, subtitle)

        bar = QRect(hud.left() + 14, hud.bottom() - 18, hud.width() - 28, 8)
        painter.fillRect(bar, _with_alpha(COLOR_OBSIDIAN, 255))
        painter.setPen(QPen(_with_alpha(accent, 180), 1))
        painter.drawRect(bar)
        fill_w = snap_pixel(bar.width() * min(1.0, p))
        painter.fillRect(bar.left(), bar.top(), fill_w, bar.height(), _with_alpha(accent, 230))
        painter.fillRect(bar.left(), bar.top(), fill_w, 2, _with_alpha(COLOR_WHITE, 190))

        if burst:
            for _ in range(random.randint(2, 6)):
                chunk_x = snap_pixel(random.randint(bar.left(), max(bar.left(), bar.right() - PIXEL_SIZE)))
                chunk_w = snap_pixel(random.choice((PIXEL_SIZE * 2, PIXEL_SIZE * 4, PIXEL_SIZE * 8)))
                chunk_w = min(chunk_w, bar.right() - chunk_x + 1)
                painter.fillRect(
                    chunk_x,
                    bar.top(),
                    max(1, chunk_w),
                    bar.height(),
                    _with_alpha(pick_palette_color(), random.randint(120, 245)),
                )

        percent = int(min(1.0, p) * 100)
        painter.setFont(_font(7))
        painter.setPen(_with_alpha(COLOR_WHITE, 210))
        painter.drawText(
            subtitle_rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"{percent:03d}%",
        )

        tag = "[CAPRI://SESSION]"
        if burst:
            tag = self._corrupt_text(tag, 0.16)
        painter.setFont(_font(8))
        painter.setPen(_with_alpha(counter, 190))
        painter.drawText(margin + jitter_x, hud.top() - 10, tag)

        if burst and random.random() < 0.55:
            painter.setFont(_font(7))
            painter.setPen(_with_alpha(accent, random.randint(150, 240)))
            painter.drawText(
                hud.left(),
                hud.bottom() + 14,
                f"ERR:{random.randrange(0x1000, 0xFFFF):04X} // {random.choice(_GLITCH_PHRASES)}",
            )

    def _paint_action_glyph(
        self,
        painter: QPainter,
        p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:
        wr = self._local_window
        size = 52
        cx = wr.center().x()
        cy = wr.top() - size - 34
        if cy < 90:
            cy = wr.bottom() + size + 34
        if self._is_glitch_burst(p):
            cx += random.choice((-8, -4, 0, 4, 8))
            cy += random.choice((-6, -3, 0, 3, 6))
        rect = QRect(cx - size // 2, cy - size // 2, size, size)

        painter.fillRect(rect.adjusted(-4, -4, 4, 4), _with_alpha(COLOR_OBSIDIAN, 225))
        pulse = 0.65 + 0.35 * math.sin(p * math.tau * 2.0)
        painter.setPen(QPen(_with_alpha(accent, int(255 * pulse)), PIXEL_SIZE))
        painter.drawRect(rect)

        if self._action == "lock":
            self._paint_lock_icon(painter, rect, accent, counter)
        elif self._action == "power_off":
            self._paint_power_icon(painter, rect, accent, counter)
        elif self._action == "suspend":
            self._paint_sleep_icon(painter, rect, accent, counter, p)
        else:
            self._paint_reboot_icon(painter, rect, accent, counter, p)

    def _paint_lock_icon(self, painter: QPainter, rect: QRect, accent: QColor, counter: QColor) -> None:
        cx = rect.center().x()
        body = QRect(cx - 14, rect.top() + 22, 28, 20)
        painter.fillRect(body, _with_alpha(accent, 230))
        painter.fillRect(body.adjusted(4, 4, -4, -4), _with_alpha(COLOR_OBSIDIAN, 240))
        painter.setPen(QPen(_with_alpha(counter, 235), PIXEL_SIZE))
        shackle = QRect(cx - 10, rect.top() + 10, 20, 22)
        painter.drawArc(shackle, 0, 180 * 16)
        painter.drawLine(cx - 10, rect.top() + 21, cx - 10, rect.top() + 24)
        painter.drawLine(cx + 10, rect.top() + 21, cx + 10, rect.top() + 24)
        painter.fillRect(cx - 2, body.top() + 7, 4, 7, _with_alpha(counter, 230))

    def _paint_power_icon(self, painter: QPainter, rect: QRect, accent: QColor, counter: QColor) -> None:
        center = rect.center()
        radius = 14
        ring = QRect(center.x() - radius, center.y() - radius + 2, radius * 2, radius * 2)
        painter.setPen(QPen(_with_alpha(accent, 235), PIXEL_SIZE * 2))
        painter.drawArc(ring, 110 * 16, 320 * 16)
        painter.fillRect(center.x() - 2, center.y() - radius - 2, 4, radius + 4, _with_alpha(counter, 240))

    def _paint_sleep_icon(
        self,
        painter: QPainter,
        rect: QRect,
        accent: QColor,
        counter: QColor,
        p: float,
    ) -> None:
        painter.setPen(QPen(_with_alpha(accent, 220), PIXEL_SIZE))
        painter.drawArc(rect.adjusted(8, 8, -8, -8), 60 * 16, 250 * 16)
        painter.setPen(QPen(_with_alpha(accent, 230), PIXEL_SIZE))
        painter.drawLine(rect.left() + 26, rect.top() + 12, rect.left() + 37, rect.top() + 12)
        painter.drawLine(rect.left() + 37, rect.top() + 12, rect.left() + 26, rect.top() + 22)
        painter.drawLine(rect.left() + 26, rect.top() + 22, rect.left() + 37, rect.top() + 22)

        painter.setFont(_font(9))
        for i in range(3):
            phase = (p * 1.8 + i * 0.33) % 1.0
            alpha = int(255 * (1.0 - phase))
            painter.setPen(_with_alpha(counter, alpha))
            painter.drawText(
                rect.right() - 18 + i * 8,
                rect.top() + 16 - int(phase * 22),
                "Z",
            )

    def _paint_reboot_icon(
        self,
        painter: QPainter,
        rect: QRect,
        accent: QColor,
        counter: QColor,
        p: float,
    ) -> None:
        center = rect.center()
        radius = 15
        arc = QRect(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        painter.setPen(QPen(_with_alpha(accent, 235), PIXEL_SIZE * 2))
        painter.drawArc(arc, int(p * 360) * 16, 280 * 16)
        painter.fillRect(arc.right() - 4, arc.top() + 2, 9, 4, _with_alpha(counter, 240))
        painter.fillRect(arc.right() + 1, arc.top() - 2, 4, 12, _with_alpha(counter, 240))


def play_session_animation(
    target: QWidget,
    action: str,
    on_finished: Callable[[], None] | None = None,
) -> SessionAnimationOverlay:
    """Запускает сессионную анимацию на экране, где находится Капри."""
    screen = target.screen() or QGuiApplication.primaryScreen()
    screen_rect = screen.geometry() if screen is not None else target.geometry()
    overlay = SessionAnimationOverlay(
        screen_rect,
        target.geometry(),
        action,
        target=target,
        on_finished=on_finished,
    )
    overlay.start()
    return overlay
