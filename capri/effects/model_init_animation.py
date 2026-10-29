from __future__ import annotations

import math
import random
from typing import Callable

from PySide6.QtCore import QElapsedTimer, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..audio.recognizer import is_model_loading, is_model_ready, model_load_failed
from ..ui.speech_sfx import get_speech_sfx
from .transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    PIXEL_SIZE,
    snap_pixel,
)

_STATUS_POLL_MS = 120
_ONLINE_HOLD_MS = 750
_FAILED_HOLD_MS = 1800


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


class ModelInitOverlay(QWidget):
    """Киберпанк-HUD инициализации нейромодели Vosk при запуске Капри."""

    finished = Signal()

    def __init__(
        self,
        screen_rect: QRect,
        model_name: str = "",
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
        self._model_name = model_name or "VOSK-MODEL-RU"
        self._on_finished = on_finished

        self._clock: QElapsedTimer | None = None
        self._elapsed = 0
        self._last_status_check = -_STATUS_POLL_MS
        self._progress = 0.0
        self._frame = 0
        self._seed = random.randrange(0, 0xFFFF)
        self._next_glitch_at = 0.18
        self._glitch_until = 0.0
        self._online_at: int | None = None
        self._failed_at: int | None = None
        self._finish_at: int | None = None
        self._finished = False

        self.setWindowTitle("Инициализация Vosk — Capri")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(self._screen_rect)

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    @property
    def is_online(self) -> bool:
        return self._online_at is not None

    @property
    def is_failed(self) -> bool:
        return self._failed_at is not None

    def start(self) -> None:
        self._clock = QElapsedTimer()
        self._clock.start()
        self.raise_()
        self.show()
        self._timer.start()
        try:
            get_speech_sfx().play_lightning_arc()
        except Exception:
            pass

    def _tick(self) -> None:
        if self._clock is None:
            return
        self._elapsed = self._clock.elapsed()
        self._frame += 1

        if self._finish_at is None:
            if self._elapsed - self._last_status_check >= _STATUS_POLL_MS:
                self._last_status_check = self._elapsed
                if is_model_ready():
                    self._mark_online()
                elif model_load_failed() or (
                    not is_model_loading() and self._elapsed > 3000
                ):
                    self._mark_failed()

        if self._online_at is not None:
            self._progress = min(
                1.0, 0.94 + (self._elapsed - self._online_at) / 300.0 * 0.06
            )
        elif self._failed_at is None:
            t = self._elapsed / 1000.0
            self._progress = min(0.94, 0.04 + 0.9 * (1.0 - math.exp(-t / 6.0)))

        self._update_glitches()
        self.update()

        if self._finish_at is not None and self._elapsed >= self._finish_at:
            self._finish()

    def _mark_online(self) -> None:
        if self._online_at is not None or self._failed_at is not None:
            return
        self._online_at = self._elapsed
        self._progress = 0.94
        self._finish_at = self._elapsed + _ONLINE_HOLD_MS
        try:
            get_speech_sfx().play_lightning_zap()
        except Exception:
            pass

    def _mark_failed(self) -> None:
        if self._online_at is not None or self._failed_at is not None:
            return
        self._failed_at = self._elapsed
        self._finish_at = self._elapsed + _FAILED_HOLD_MS
        try:
            get_speech_sfx().play_close()
        except Exception:
            pass

    def _update_glitches(self) -> None:
        if self._elapsed < self._next_glitch_at:
            return
        power = 1.0 if self._online_at is not None or self._failed_at is not None else 0.45
        self._glitch_until = self._elapsed + random.randint(90, 190)
        self._next_glitch_at = self._elapsed + random.uniform(420, 900) * (1.0 / power)
        self._seed = random.randrange(0, 0xFFFF)

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

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p = self._progress
        elapsed = self._elapsed

        appear = min(1.0, elapsed / 320.0)
        painter.fillRect(self.rect(), _with_alpha(COLOR_OBSIDIAN, int(170 * appear)))

        self._paint_scanlines(painter, appear)
        self._paint_glitches(painter, appear)

        panel = self._panel_rect()
        self._paint_panel(painter, panel, p, appear)

        painter.end()

    def _panel_rect(self) -> QRect:
        width = max(360, min(self.width() - 100, 760))
        height = max(270, min(self.height() - 120, 276))
        x = (self.width() - width) // 2
        y = (self.height() - height) // 2
        return QRect(snap_pixel(x), snap_pixel(y), snap_pixel(width), snap_pixel(height))

    def _paint_scanlines(self, painter: QPainter, appear: float) -> None:
        alpha = int(48 * appear)
        painter.setPen(QPen(_with_alpha(COLOR_OBSIDIAN, alpha), 2))
        for y in range(0, self.height(), PIXEL_SIZE):
            painter.drawLine(0, y, self.width(), y)

    def _paint_glitches(self, painter: QPainter, appear: float) -> None:
        if self._elapsed > self._glitch_until:
            return
        rng = random.Random(self._seed + self._frame * 53)
        for _ in range(rng.randint(4, 10)):
            y = snap_pixel(rng.randint(0, max(0, self.height() - 1)))
            height = rng.choice((PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 4))
            width = snap_pixel(rng.randint(self.width() // 10, max(self.width() // 10 + 1, self.width() // 2)))
            x = snap_pixel(rng.randint(-width // 3, self.width()))
            color = rng.choice(
                (COLOR_CRIMSON, COLOR_ACID_GREEN, COLOR_ELECTRIC_BLUE, COLOR_VIOLET)
            )
            painter.fillRect(
                x, y, width, height, _with_alpha(color, int(rng.randint(45, 150) * appear))
            )

    def _paint_panel(
        self, painter: QPainter, panel: QRect, progress: float, appear: float
    ) -> None:
        rng = random.Random(self._seed + self._frame * 17)
        online = self._online_at is not None
        failed = self._failed_at is not None
        accent = COLOR_ACID_GREEN if online else COLOR_CRIMSON
        base_alpha = int(238 * appear)

        painter.fillRect(panel, _with_alpha(COLOR_OBSIDIAN, base_alpha))

        # Сканлайны и лёгкий шум внутри панели.
        painter.save()
        painter.setClipRect(panel)
        painter.setPen(QPen(_with_alpha(COLOR_CRIMSON, 20), 1))
        for y in range(panel.top() + 2, panel.bottom(), 3):
            painter.drawLine(panel.left() + 2, y, panel.right() - 2, y)

        # Бегущая полоса сканирования.
        if appear >= 1.0 and not failed:
            sweep = (self._elapsed // 4) % max(1, panel.height())
            painter.fillRect(
                panel.left() + 1,
                panel.top() + sweep,
                panel.width() - 2,
                PIXEL_SIZE,
                _with_alpha(COLOR_ACID_GREEN, 36),
            )

        if self._elapsed <= self._glitch_until:
            for _ in range(rng.randint(2, 5)):
                gy = snap_pixel(
                    rng.randint(panel.top(), max(panel.top() + 1, panel.bottom()))
                )
                gh = rng.choice((PIXEL_SIZE, PIXEL_SIZE * 2))
                painter.fillRect(
                    panel.left(),
                    gy,
                    panel.width(),
                    gh,
                    _with_alpha(rng.choice((COLOR_CRIMSON, COLOR_ELECTRIC_BLUE)), rng.randint(40, 120)),
                )
        painter.restore()

        # Двойная рамка и срезанный угол.
        painter.setPen(QPen(_with_alpha(accent, base_alpha), 2))
        painter.drawRect(panel.adjusted(1, 1, -1, -1))
        painter.setPen(QPen(_with_alpha(COLOR_WHITE, int(120 * appear)), 1))
        painter.drawRect(panel.adjusted(5, 5, -5, -5))

        cut = 16
        painter.fillRect(
            QRect(panel.right() - cut + 1, panel.top(), cut, cut),
            _with_alpha(COLOR_OBSIDIAN, base_alpha),
        )
        painter.setPen(QPen(_with_alpha(accent, base_alpha), 2))
        painter.drawLine(
            panel.right() - cut, panel.top() + 1, panel.right() - 1, panel.top() + cut
        )

        # Заголовок HUD.
        header = QRect(panel.left() + 18, panel.top() + 14, panel.width() - 36, 18)
        painter.setFont(_font(9))
        painter.setPen(_with_alpha(COLOR_ACID_GREEN, int(230 * appear)))
        painter.drawText(
            header, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "CAPRI//NEURAL_INTERFACE",
        )
        painter.setPen(_with_alpha(COLOR_WHITE, int(180 * appear)))
        painter.drawText(
            header, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "BOOT SEQ // 07",
        )
        line_y = panel.top() + 38
        painter.setPen(QPen(_with_alpha(COLOR_CRIMSON, int(210 * appear)), 1))
        painter.drawLine(panel.left() + 18, line_y, panel.right() - 18, line_y)

        # Заголовок и состояние.
        title = QRect(panel.left() + 18, panel.top() + 52, panel.width() - 36, 30)
        if online:
            title_text = "VOSK CORE // ONLINE"
        elif failed:
            title_text = "VOSK CORE // FAILED"
        else:
            title_text = "VOSK CORE // INITIALIZING"

        if self._elapsed <= self._glitch_until:
            painter.setFont(_font(15))
            painter.setPen(_with_alpha(COLOR_ELECTRIC_BLUE, int(100 * appear)))
            painter.drawText(
                title.translated(rng.choice((-6, -3, 3, 6)), 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                title_text,
            )
            painter.setPen(_with_alpha(COLOR_CRIMSON, int(120 * appear)))
            painter.drawText(
                title.translated(rng.choice((-4, 4)), 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                title_text,
            )

        painter.setFont(_font(15))
        painter.setPen(_with_alpha(COLOR_WHITE, int(245 * appear)))
        painter.drawText(
            title,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title_text,
        )

        subtitle = QRect(panel.left() + 18, panel.top() + 88, panel.width() - 36, 18)
        painter.setFont(_font(8))
        painter.setPen(_with_alpha(COLOR_CRIMSON, int(220 * appear)))
        subtitle_text = (
            "RUSSIAN ACOUSTIC MODEL // READY"
            if online
            else "RUSSIAN ACOUSTIC MODEL // MEMORY MAPPING"
            if not failed
            else "RUSSIAN ACOUSTIC MODEL // LOAD ERROR"
        )
        painter.drawText(
            subtitle,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            subtitle_text,
        )

        model_line = QRect(panel.left() + 18, panel.top() + 112, panel.width() - 36, 18)
        painter.setFont(_font(9))
        painter.setPen(_with_alpha(COLOR_ACID_GREEN if not failed else COLOR_CRIMSON, int(230 * appear)))
        painter.drawText(
            model_line,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._model_name.upper(),
        )

        # Сегментированный прогресс-бар.
        bar = QRect(panel.left() + 18, panel.top() + 146, panel.width() - 36, 20)
        painter.setPen(QPen(_with_alpha(COLOR_VIOLET, int(190 * appear)), 1))
        painter.drawRect(bar)
        segments = 40
        gap = 3
        seg_width = max(2, (bar.width() - gap * (segments + 1)) // segments)
        filled = int(segments * progress)
        for index in range(segments):
            x = bar.left() + gap + index * (seg_width + gap)
            seg = QRect(x, bar.top() + 5, seg_width, bar.height() - 10)
            if index < filled:
                painter.fillRect(seg, _with_alpha(COLOR_ACID_GREEN if not failed else COLOR_CRIMSON, int(220 * appear)))
            elif index == filled and not online and not failed:
                painter.fillRect(seg, _with_alpha(COLOR_WHITE, int(230 * appear)))
            else:
                painter.fillRect(seg, _with_alpha(COLOR_VIOLET, int(60 * appear)))

        percent = QRect(panel.left() + 18, panel.top() + 172, panel.width() - 36, 18)
        painter.setFont(_font(10))
        painter.setPen(_with_alpha(COLOR_WHITE, int(230 * appear)))
        painter.drawText(
            percent,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{int(progress * 100):03d}%",
        )
        state_text = "ONLINE" if online else "FAILED" if failed else "LOADING"
        state_color = COLOR_ACID_GREEN if online else COLOR_CRIMSON
        painter.setPen(_with_alpha(state_color, int(235 * appear)))
        painter.drawText(
            percent,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            state_text,
        )

        # Телеметрия загрузки.
        telemetry = QRect(panel.left() + 18, panel.top() + 200, panel.width() - 36, 46)
        painter.setFont(_font(7))
        rows = (
            ("MEM//MAP", f"{int(progress * 3584):04d} MB"),
            ("DECODER", "READY" if online else "SYNCING" if not failed else "FAULT"),
            ("WAVEFORM", "16 kHz // MONO"),
        )
        for row, (key, value) in enumerate(rows):
            row_rect = QRect(
                telemetry.left(),
                telemetry.top() + row * 14,
                telemetry.width(),
                13,
            )
            painter.setPen(_with_alpha(COLOR_CRIMSON, int(190 * appear)))
            painter.drawText(
                row_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                key,
            )
            painter.setPen(_with_alpha(COLOR_WHITE, int(200 * appear)))
            painter.drawText(
                row_rect,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                value,
            )

        # Угловые засечки и акцентные штрихи.
        painter.setPen(QPen(_with_alpha(COLOR_ACID_GREEN, int(220 * appear)), 2))
        painter.drawLine(panel.left() + 8, panel.bottom() - 8, panel.left() + 8, panel.bottom() - 28)
        painter.drawLine(panel.left() + 8, panel.bottom() - 8, panel.left() + 30, panel.bottom() - 8)
        painter.setPen(QPen(_with_alpha(COLOR_CRIMSON, int(220 * appear)), 2))
        painter.drawLine(panel.right() - 8, panel.top() + 8, panel.right() - 8, panel.top() + 28)
