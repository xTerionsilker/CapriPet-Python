"""Киберпанк-оверлеи для системных действий сессии (выключение, сон, блокировка)."""

from __future__ import annotations

import contextlib
import math
import random
from collections.abc import Callable

from PySide6.QtCore import QElapsedTimer, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

from ..ui.speech_sfx import get_speech_sfx
from .session_anim_helpers import (
    _GLITCH_GLYPHS,
    _GLITCH_PHRASES,
    SessionAnimEffectsMixin,
    _font,
    _with_alpha,
)
from .transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    PIXEL_SIZE,
    CyberPixelSpark,
    pick_palette_color,
    snap_pixel,
)

SESSION_ANIMATION_DURATION_MS = 1500
SESSION_ACTION_LEAD_MS = 1800


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


class SessionAnimationOverlay(QWidget, SessionAnimEffectsMixin):
    """Оверлей киберпанк-анимации при выполнении сессионных действий системы."""

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
        if (
            target is not None
            and target.width() > 0
            and target.height() > 0
        ):
            try:
                self._target_pixmap = target.grab()
            except Exception:  # noqa: BLE001
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
        with contextlib.suppress(Exception):
            get_speech_sfx().play_session_action(self._action)

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
            with contextlib.suppress(Exception):
                sfx = get_speech_sfx()
                if self._action == "reboot":
                    sfx.play_lightning_zap()
                elif self._action == "power_off":
                    sfx.play_lightning_strike()
                elif self._action == "lock":
                    sfx.play_lightning_arc()

        self._spawn_action_particles(p, dt)
        self._particles = [
            particle for particle in self._particles if particle.step(dt)
        ]
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
            with contextlib.suppress(Exception):
                get_speech_sfx().play_lightning_zap()

    @staticmethod
    def _glitch_power(p: float) -> float:

        t = max(0.0, min(1.0, (p - 0.12) / 0.88))
        return 0.2 + 1.8 * (t**1.6)

    def _is_glitch_burst(self, p: float) -> bool:
        return p <= self._burst_until

    @staticmethod
    def _corrupt_text(text: str, probability: float) -> str:
        if probability <= 0.0:
            return text
        return "".join(
            random.choice(_GLITCH_GLYPHS)
            if random.random() < probability
            else char
            for char in text
        )

    def _finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._timer.stop()
        self.finished.emit()
        if self._on_finished is not None:
            with contextlib.suppress(Exception):
                self._on_finished()
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
        accent = QColor(self._profile["accent"])
        for _ in range(2):
            x = wr.center().x() + random.randint(
                -wr.width() // 2, wr.width() // 2
            )
            y = wr.center().y() + random.randint(
                -wr.height() // 2, wr.height() // 2
            )
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
                vx = random.choice((-1.0, 1.0)) * random.uniform(
                    80.0, 220.0
                )
                vy = random.uniform(-30.0, 30.0)
            self._particles.append(
                CyberPixelSpark(
                    snap_pixel(x),
                    snap_pixel(y),
                    vx,
                    vy,
                    color=accent
                    if random.random() < 0.65
                    else pick_palette_color(),
                    size=random.choice((PIXEL_SIZE, PIXEL_SIZE * 2)),
                    life=random.uniform(0.25, 0.60),
                    kind=random.choice(("spark", "bit", "bar")),
                )
            )

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p = self._progress
        accent = QColor(self._profile["accent"])
        counter = QColor(self._profile["counter"])

        backdrop = 110 + 45 * math.sin(p * math.pi) + 120 * (p**2)
        painter.fillRect(
            self.rect(), _with_alpha(COLOR_OBSIDIAN, int(backdrop))
        )

        self._paint_scanlines(painter, accent, p)
        self._paint_target(painter, p, accent, counter)
        self._paint_screen_glitches(painter, p, accent, counter)

        # Кинематографические процедурные слои для каждого действия
        self._paint_action_scene(painter, p, accent, counter)

        self._paint_hud(painter, p, accent, counter)
        self._paint_action_glyph(painter, p, accent, counter)

        for particle in self._particles:
            particle.draw(painter)

        if 0.10 <= p <= 0.88:
            flash_p = (p - 0.10) / 0.78
            self._paint_flash(painter, flash_p, accent, counter)

        self._paint_screen_takeover(painter, p, accent, counter)
        painter.end()

    def _paint_action_scene(
        self,
        painter: QPainter,
        p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:
        """Отрисовывает специализированную сюжетную сцену действия."""
        if self._action == "lock":
            self._paint_lockdown_lasers(painter, self.rect(), p, accent, counter)
        elif self._action == "power_off":
            self._paint_crt_beam_collapse(painter, self.rect(), p, accent, counter)
        elif self._action == "reboot":
            self._paint_reboot_rings(painter, self.rect(), p, accent, counter)
        elif self._action == "suspend":
            self._paint_cryostasis_waves(painter, self.rect(), p, accent, counter)

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
            hud_y = min(
                self.height() - hud_height - margin, wr.bottom() + 20
            )

        burst = self._is_glitch_burst(p)
        jitter_x = random.choice((-6, -4, 0, 0, 4, 6)) if burst else 0
        jitter_y = random.choice((-4, 0, 0, 4)) if burst else 0
        hud = QRect(
            hud_x + jitter_x, hud_y + jitter_y, hud_width, hud_height
        )

        painter.fillRect(hud, _with_alpha(COLOR_OBSIDIAN, 225))
        painter.setPen(QPen(_with_alpha(accent, 230), PIXEL_SIZE))
        painter.drawRect(hud)
        if burst:
            painter.setPen(
                QPen(_with_alpha(counter, random.randint(90, 200)), 1)
            )
            painter.drawRect(hud.adjusted(2, 2, -2, -2))

        title = str(self._profile["title"])
        subtitle = str(self._profile["subtitle"])
        if burst:
            power = self._glitch_power(p)
            title = self._corrupt_text(
                title, min(0.75, 0.12 + power * 0.22)
            )
            subtitle = self._corrupt_text(
                subtitle, min(0.55, 0.06 + power * 0.16)
            )

        title_rect = hud.adjusted(14, 12, -14, -40)
        painter.setFont(_font(12))
        if burst:
            painter.setPen(_with_alpha(COLOR_CRIMSON, 220))
            painter.drawText(
                title_rect.translated(-PIXEL_SIZE, 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                title,
            )
            painter.setPen(_with_alpha(COLOR_ACID_GREEN, 200))
            painter.drawText(
                title_rect.translated(PIXEL_SIZE, 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                title,
            )
        painter.setPen(_with_alpha(COLOR_WHITE, 240))
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )

        subtitle_rect = hud.adjusted(14, 38, -14, -22)
        painter.setFont(_font(7))
        painter.setPen(_with_alpha(counter, 220))
        painter.drawText(
            subtitle_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            subtitle,
        )

        progress_bar = QRect(
            hud.left() + 14, hud.bottom() - 18, hud.width() - 28, 8
        )
        painter.fillRect(progress_bar, _with_alpha(COLOR_OBSIDIAN, 255))
        painter.setPen(QPen(_with_alpha(accent, 180), 1))
        painter.drawRect(progress_bar)
        fill_w = snap_pixel(progress_bar.width() * min(1.0, p))
        painter.fillRect(
            progress_bar.left(),
            progress_bar.top(),
            fill_w,
            progress_bar.height(),
            _with_alpha(accent, 230),
        )
        painter.fillRect(
            progress_bar.left(), progress_bar.top(), fill_w, 2, _with_alpha(COLOR_WHITE, 190)
        )

        if burst:
            for _ in range(random.randint(2, 6)):
                chunk_x = snap_pixel(
                    random.randint(
                        progress_bar.left(),
                        max(progress_bar.left(), progress_bar.right() - PIXEL_SIZE),
                    )
                )
                chunk_w = snap_pixel(
                    random.choice(
                        (PIXEL_SIZE * 2, PIXEL_SIZE * 4, PIXEL_SIZE * 8)
                    )
                )
                chunk_w = min(chunk_w, progress_bar.right() - chunk_x + 1)
                painter.fillRect(
                    chunk_x,
                    progress_bar.top(),
                    max(1, chunk_w),
                    progress_bar.height(),
                    _with_alpha(
                        pick_palette_color(), random.randint(120, 245)
                    ),
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

        painter.fillRect(
            rect.adjusted(-4, -4, 4, 4), _with_alpha(COLOR_OBSIDIAN, 225)
        )
        pulse = 0.65 + 0.35 * math.sin(p * math.tau * 2.0)
        painter.setPen(
            QPen(_with_alpha(accent, int(255 * pulse)), PIXEL_SIZE)
        )
        painter.drawRect(rect)

        if self._action == "lock":
            self._paint_lock_icon(painter, rect, accent, counter)
        elif self._action == "power_off":
            self._paint_power_icon(painter, rect, accent, counter)
        elif self._action == "suspend":
            self._paint_sleep_icon(painter, rect, accent, counter, p)
        else:
            self._paint_reboot_icon(painter, rect, accent, counter, p)

    def _paint_lock_icon(
        self,
        painter: QPainter,
        rect: QRect,
        accent: QColor,
        counter: QColor,
    ) -> None:
        cx = rect.center().x()
        body = QRect(cx - 14, rect.top() + 22, 28, 20)
        painter.fillRect(body, _with_alpha(accent, 230))
        painter.fillRect(
            body.adjusted(4, 4, -4, -4), _with_alpha(COLOR_OBSIDIAN, 240)
        )
        painter.setPen(QPen(_with_alpha(counter, 235), PIXEL_SIZE))
        shackle = QRect(cx - 10, rect.top() + 10, 20, 22)
        painter.drawArc(shackle, 0, 180 * 16)
        painter.drawLine(
            cx - 10, rect.top() + 21, cx - 10, rect.top() + 24
        )
        painter.drawLine(
            cx + 10, rect.top() + 21, cx + 10, rect.top() + 24
        )
        painter.fillRect(
            cx - 2, body.top() + 7, 4, 7, _with_alpha(counter, 230)
        )

    def _paint_power_icon(
        self,
        painter: QPainter,
        rect: QRect,
        accent: QColor,
        counter: QColor,
    ) -> None:
        center = rect.center()
        radius = 14
        ring = QRect(
            center.x() - radius,
            center.y() - radius + 2,
            radius * 2,
            radius * 2,
        )
        painter.setPen(QPen(_with_alpha(accent, 235), PIXEL_SIZE * 2))
        painter.drawArc(ring, 110 * 16, 320 * 16)
        painter.fillRect(
            center.x() - 2,
            center.y() - radius - 2,
            4,
            radius + 4,
            _with_alpha(counter, 240),
        )

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
        painter.drawLine(
            rect.left() + 26,
            rect.top() + 12,
            rect.left() + 37,
            rect.top() + 12,
        )
        painter.drawLine(
            rect.left() + 37,
            rect.top() + 12,
            rect.left() + 26,
            rect.top() + 22,
        )
        painter.drawLine(
            rect.left() + 26,
            rect.top() + 22,
            rect.left() + 37,
            rect.top() + 22,
        )

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
        arc = QRect(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2,
        )
        painter.setPen(QPen(_with_alpha(accent, 235), PIXEL_SIZE * 2))
        painter.drawArc(arc, int(p * 360) * 16, 280 * 16)
        painter.fillRect(
            arc.right() - 4, arc.top() + 2, 9, 4, _with_alpha(counter, 240)
        )
        painter.fillRect(
            arc.right() + 1,
            arc.top() - 2,
            4,
            12,
            _with_alpha(counter, 240),
        )


class LockdownSceneOverlay(SessionAnimationOverlay):
    """Специализированный оверлей для действия 'lock' (Смертоносный локдаун)."""

    def __init__(
        self,
        screen_rect: QRect,
        window_rect: QRect,
        target: QWidget | None = None,
        parent: QWidget | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            screen_rect,
            window_rect,
            action="lock",
            target=target,
            parent=parent,
            on_finished=on_finished,
        )


class DisconnectSceneOverlay(SessionAnimationOverlay):
    """Специализированный оверлей для действия 'power_off' (Разрыв нейросвязи)."""

    def __init__(
        self,
        screen_rect: QRect,
        window_rect: QRect,
        target: QWidget | None = None,
        parent: QWidget | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            screen_rect,
            window_rect,
            action="power_off",
            target=target,
            parent=parent,
            on_finished=on_finished,
        )


class RebootCycleOverlay(SessionAnimationOverlay):
    """Специализированный оверлей для действия 'reboot' (Цикл буйного перезапуска)."""

    def __init__(
        self,
        screen_rect: QRect,
        window_rect: QRect,
        target: QWidget | None = None,
        parent: QWidget | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            screen_rect,
            window_rect,
            action="reboot",
            target=target,
            parent=parent,
            on_finished=on_finished,
        )


class CryostasisSceneOverlay(SessionAnimationOverlay):
    """Специализированный оверлей для действия 'suspend' (Криостазис)."""

    def __init__(
        self,
        screen_rect: QRect,
        window_rect: QRect,
        target: QWidget | None = None,
        parent: QWidget | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            screen_rect,
            window_rect,
            action="suspend",
            target=target,
            parent=parent,
            on_finished=on_finished,
        )


def play_session_animation(
    target: QWidget,
    action: str,
    on_finished: Callable[[], None] | None = None,
) -> SessionAnimationOverlay:
    """Создает и запускает специализированный сюжетный оверлей сессионного действия."""
    screen = target.screen() or QGuiApplication.primaryScreen()
    screen_rect = (
        screen.geometry() if screen is not None else target.geometry()
    )
    window_rect = target.geometry()

    overlay_cls: type[SessionAnimationOverlay]
    if action == "lock":
        overlay_cls = LockdownSceneOverlay
    elif action in ("power_off", "poweroff"):
        overlay_cls = DisconnectSceneOverlay
    elif action == "reboot":
        overlay_cls = RebootCycleOverlay
    elif action in ("suspend", "sleep"):
        overlay_cls = CryostasisSceneOverlay
    else:
        overlay_cls = SessionAnimationOverlay

    if overlay_cls is SessionAnimationOverlay:
        overlay = SessionAnimationOverlay(
            screen_rect,
            window_rect,
            action,
            target=target,
            on_finished=on_finished,
        )
    else:
        overlay = overlay_cls(  # type: ignore[call-arg]
            screen_rect,
            window_rect,
            target=target,
            on_finished=on_finished,
        )
    overlay.start()
    return overlay
