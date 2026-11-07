"""Вспомогательные методы отрисовки и эффектов для анимаций сессии."""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from capri.ui.theme import get_hud_font

from .transition_base import (
    BAYER_4X4,
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    PIXEL_SIZE,
    pick_palette_color,
    snap_pixel,
)
from .transition_painters import (
    CyberHoloReticle,
    CyberShockwaveRing,
)

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

def _font(size: int) -> QFont:
    return get_hud_font(size, bold=True)


def _with_alpha(color: QColor, alpha: int) -> QColor:
    result = QColor(color)
    result.setAlpha(max(0, min(255, int(alpha))))
    return result



class SessionAnimEffectsMixin:
    """Миксин эффектов отрисовки глитчей, сканирования и таргета."""

    def _paint_scanlines(
        self, painter: QPainter, accent: QColor, p: float
    ) -> None:
        alpha = int(38 + 28 * math.sin(p * math.pi * 6.0))
        painter.setPen(QPen(_with_alpha(COLOR_OBSIDIAN, alpha), 2))
        for y in range(0, self.height(), PIXEL_SIZE):
            painter.drawLine(0, y, self.width(), y)

        sweep_y = snap_pixel(int(self.height() * min(1.0, p * 1.15)))
        painter.fillRect(
            0,
            sweep_y,
            self.width(),
            PIXEL_SIZE * 2,
            _with_alpha(accent, 95),
        )
        painter.fillRect(
            0,
            sweep_y - PIXEL_SIZE * 2,
            self.width(),
            PIXEL_SIZE * 2,
            _with_alpha(COLOR_WHITE, 28),
        )

        if self._is_glitch_burst(p):
            power = self._glitch_power(p)
            for _ in range(1 + int(power)):
                roll_y = snap_pixel(
                    random.randint(
                        0, max(0, self.height() - PIXEL_SIZE * 12)
                    )
                )
                roll_h = random.choice(
                    (
                        PIXEL_SIZE * 4,
                        PIXEL_SIZE * 8,
                        PIXEL_SIZE * 16,
                        PIXEL_SIZE * 32,
                    )
                )
                painter.fillRect(
                    0,
                    roll_y,
                    self.width(),
                    roll_h,
                    _with_alpha(
                        COLOR_OBSIDIAN,
                        random.randint(80, min(245, int(90 + 80 * power))),
                    ),
                )
                painter.fillRect(
                    0,
                    roll_y + roll_h,
                    self.width(),
                    PIXEL_SIZE,
                    _with_alpha(
                        COLOR_ACID_GREEN,
                        random.randint(40, min(240, int(70 + 75 * power))),
                    ),
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

        tear_count = (
            rng.randint(5, 13) if burst else rng.randint(0, 2)
        ) * max(1, int(power))
        for _ in range(tear_count):
            y = snap_pixel(rng.randint(0, max(0, h - 1)))
            tear_h = rng.choice(
                (
                    PIXEL_SIZE,
                    PIXEL_SIZE * 2,
                    PIXEL_SIZE * 4,
                    PIXEL_SIZE * 8,
                )
            )
            x = snap_pixel(rng.randint(-w // 5, w))
            tear_w = snap_pixel(
                rng.randint(w // 12, max(w // 12 + 1, w // 2))
            )
            color = pick_palette_color()
            painter.fillRect(
                x,
                y,
                tear_w,
                tear_h,
                _with_alpha(
                    color, rng.randint(55, min(255, int(85 + 90 * power)))
                ),
            )

        if burst:
            for _ in range(max(3, int(2 + power * 3))):
                y = snap_pixel(rng.randint(0, max(0, h - PIXEL_SIZE * 6)))
                band_h = rng.choice(
                    (PIXEL_SIZE, PIXEL_SIZE * 2, PIXEL_SIZE * 4)
                )
                shift = rng.choice(
                    (
                        -PIXEL_SIZE * 8,
                        -PIXEL_SIZE * 4,
                        -PIXEL_SIZE * 2,
                        PIXEL_SIZE * 2,
                        PIXEL_SIZE * 4,
                        PIXEL_SIZE * 8,
                    )
                )
                painter.fillRect(
                    shift,
                    y,
                    w,
                    band_h,
                    _with_alpha(
                        COLOR_CRIMSON, min(230, int(45 + 55 * power))
                    ),
                )
                painter.fillRect(
                    -shift,
                    y + PIXEL_SIZE,
                    w,
                    band_h,
                    _with_alpha(
                        COLOR_ACID_GREEN, min(220, int(35 + 45 * power))
                    ),
                )

        if (
            burst
            and self._target_pixmap is not None
            and not self._target_pixmap.isNull()
        ):
            pw = self._target_pixmap.width()
            ph = self._target_pixmap.height()
            for _ in range(int(rng.randint(5, 12) * (0.7 + power * 0.75))):
                bw = snap_pixel(
                    rng.randint(
                        PIXEL_SIZE * 4,
                        max(PIXEL_SIZE * 5, wr.width() // 2),
                    )
                )
                bh = snap_pixel(
                    rng.randint(
                        PIXEL_SIZE * 2,
                        max(PIXEL_SIZE * 3, wr.height() // 4),
                    )
                )
                sx = snap_pixel(rng.randint(0, max(0, pw - bw)))
                sy = snap_pixel(rng.randint(0, max(0, ph - bh)))
                dx = snap_pixel(
                    wr.left()
                    + rng.randint(
                        -wr.width() * (1 + int(power)),
                        wr.width() * (1 + int(power)),
                    )
                )
                dy = snap_pixel(
                    wr.top()
                    + rng.randint(
                        -wr.height() * (1 + int(power)),
                        wr.height() * (1 + int(power)),
                    )
                )
                src = QRect(sx, sy, min(bw, pw - sx), min(bh, ph - sy))
                if src.width() <= 0 or src.height() <= 0:
                    continue
                painter.drawPixmap(
                    QRect(dx, dy, src.width(), src.height()),
                    self._target_pixmap,
                    src,
                )
                painter.fillRect(
                    QRect(dx, dy, src.width(), src.height()),
                    _with_alpha(
                        rng.choice(
                            (
                                COLOR_CRIMSON,
                                COLOR_ACID_GREEN,
                                COLOR_ELECTRIC_BLUE,
                                COLOR_VIOLET,
                            )
                        ),
                        rng.randint(28, min(210, int(45 + 65 * power))),
                    ),
                )

        noise_base = rng.randint(45, 150) if burst else rng.randint(6, 18)
        noise_count = int(noise_base * (0.65 + power * 0.9))
        for _ in range(noise_count):
            nx = snap_pixel(rng.randint(0, max(0, w - 1)))
            ny = snap_pixel(rng.randint(0, max(0, h - 1)))
            size = rng.choice(
                (
                    PIXEL_SIZE,
                    PIXEL_SIZE * 2,
                    PIXEL_SIZE * 4,
                    PIXEL_SIZE * 8,
                )
            )
            painter.fillRect(
                nx,
                ny,
                size,
                size,
                _with_alpha(
                    pick_palette_color(),
                    rng.randint(70, min(255, int(150 + 65 * power))),
                ),
            )

        if burst and rng.random() < min(0.98, 0.55 + 0.2 * power):
            phrase = rng.choice(_GLITCH_PHRASES)
            painter.setFont(_font(rng.choice((8, 10, 12, 16))))
            tx = snap_pixel(rng.randint(20, max(21, w - 420)))
            ty = snap_pixel(rng.randint(30, max(31, h - 30)))
            shift = rng.choice((PIXEL_SIZE, PIXEL_SIZE * 2))
            painter.setPen(
                _with_alpha(COLOR_CRIMSON, rng.randint(150, 240))
            )
            painter.drawText(tx - shift, ty, phrase)
            painter.setPen(
                _with_alpha(COLOR_ACID_GREEN, rng.randint(120, 210))
            )
            painter.drawText(tx + shift, ty, phrase)
            painter.setPen(_with_alpha(COLOR_WHITE, rng.randint(180, 255)))
            painter.drawText(tx, ty, phrase)

        if burst:
            edge_h = snap_pixel(
                rng.randint(PIXEL_SIZE * 8, max(PIXEL_SIZE * 9, h // 8))
            )
            edge_y = snap_pixel(rng.randint(0, max(0, h - edge_h)))
            painter.fillRect(
                0,
                edge_y,
                rng.choice((PIXEL_SIZE * 2, PIXEL_SIZE * 4)),
                edge_h,
                _with_alpha(accent, rng.randint(100, 220)),
            )
            painter.fillRect(
                w - PIXEL_SIZE * 3,
                edge_y,
                PIXEL_SIZE * 3,
                edge_h,
                _with_alpha(counter, rng.randint(90, 190)),
            )
            if rng.random() < 0.55:
                cut_y = snap_pixel(
                    rng.randint(0, max(0, h - PIXEL_SIZE * 8))
                )
                painter.fillRect(
                    0,
                    cut_y,
                    w,
                    rng.choice((PIXEL_SIZE * 2, PIXEL_SIZE * 4)),
                    _with_alpha(COLOR_OBSIDIAN, rng.randint(150, 245)),
                )

    def _paint_screen_takeover(
        self,
        painter: QPainter,
        p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:

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
        painter.setClipRect(
            wr.adjusted(
                -PIXEL_SIZE * 8,
                -PIXEL_SIZE * 8,
                PIXEL_SIZE * 8,
                PIXEL_SIZE * 8,
            )
        )
        self._paint_target_slices(painter, wr, p, accent, counter)
        painter.restore()

        if self._action == "lock":
            offset = int((1.0 - min(1.0, p / 0.65)) * 48)
            CyberHoloReticle.draw(
                painter,
                wr,
                min(1.0, p / 0.55),
                color=accent,
                bracket_offset=offset,
            )
        elif self._action == "reboot":
            self._paint_rotation_ring(painter, wr, p, accent, counter)
        elif self._action == "suspend":
            self._paint_stasis_field(painter, wr, p, accent)
        else:
            CyberHoloReticle.draw(
                painter, wr, max(0.0, 1.0 - p), color=accent
            )

    def _paint_target_slices(
        self,
        painter: QPainter,
        wr: QRect,
        p: float,
        accent: QColor,
        counter: QColor,
    ) -> None:
        if self._target_pixmap is None or self._target_pixmap.isNull():
            painter.fillRect(
                wr,
                _with_alpha(accent, int(35 + 30 * math.sin(p * math.pi))),
            )
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
                dx = snap_pixel(
                    random.uniform(-1.0, 1.0) * w * 0.35 * settle
                )
                dy = 0
            elif self._action == "power_off":
                collapse = max(0.0, (p - 0.35) / 0.65)
                dy = snap_pixel((y_ratio - 0.5) * h * collapse)
                dx = snap_pixel(
                    random.uniform(-1.0, 1.0) * w * 0.10 * (1.0 - collapse)
                )
            elif self._action == "suspend":
                dy = snap_pixel(
                    math.sin(p * math.tau * 2.0 + i * 0.7)
                    * 4.0
                    * intensity
                )
                dx = snap_pixel(math.sin(p * math.tau + i * 0.4) * 3.0)
            else:
                scatter = math.sin(p * math.pi)
                angle = (i / slice_count) * math.tau + p * math.tau
                dx = snap_pixel(math.cos(angle) * w * 0.12 * scatter)
                dy = snap_pixel(math.sin(angle) * h * 0.08 * scatter)

            if self._is_glitch_burst(p):
                power = self._glitch_power(p)
                dx += snap_pixel(
                    random.uniform(-1.0, 1.0) * w * 0.22 * power
                )
                if random.random() < 0.35:
                    dy += snap_pixel(
                        random.uniform(-1.0, 1.0) * h * 0.05 * power
                    )

            src = QRect(0, sy, w, sh)
            dst = QRect(wr.left() + dx, wr.top() + sy + dy, w, sh)
            painter.drawPixmap(dst, pixmap, src)

            if self._is_glitch_burst(p) and random.random() < 0.45:
                ghost_shift = random.choice(
                    (
                        -PIXEL_SIZE * 3,
                        -PIXEL_SIZE * 2,
                        PIXEL_SIZE * 2,
                        PIXEL_SIZE * 3,
                    )
                )
                painter.setOpacity(0.34)
                painter.drawPixmap(
                    dst.translated(ghost_shift, 0), pixmap, src
                )
                painter.setOpacity(1.0)
                painter.fillRect(
                    dst.translated(ghost_shift, 0),
                    _with_alpha(
                        COLOR_CRIMSON
                        if ghost_shift < 0
                        else COLOR_ACID_GREEN,
                        random.randint(35, 75),
                    ),
                )

        if self._action == "suspend":
            tint = _with_alpha(accent, int(75 * intensity))
            painter.fillRect(wr, tint)
        elif self._action == "power_off":
            collapse = max(0.0, (p - 0.50) / 0.50)
            line_h = max(PIXEL_SIZE, snap_pixel(h * (1.0 - collapse)))
            line_rect = QRect(
                wr.center().x() - w // 2,
                wr.center().y() - line_h // 2,
                w,
                line_h,
            )
            painter.fillRect(line_rect, _with_alpha(COLOR_OBSIDIAN, 235))
            painter.fillRect(
                line_rect.adjusted(0, line_h // 2 - PIXEL_SIZE, 0, 0),
                _with_alpha(counter, 220),
            )
        elif self._action == "lock":
            bar_y = wr.top() + snap_pixel((p * 1.3 % 1.0) * h)
            painter.fillRect(
                wr.left(),
                bar_y,
                w,
                PIXEL_SIZE * 2,
                _with_alpha(counter, 160),
            )

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
        rect = QRect(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2,
        )
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
        rect = QRect(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2,
        )
        painter.setPen(QPen(_with_alpha(accent, 170), PIXEL_SIZE))
        painter.drawEllipse(rect)
        wave_radius = radius + int(14 * math.sin(p * math.tau * 2.0))
        painter.setPen(QPen(_with_alpha(COLOR_VIOLET, 120), PIXEL_SIZE))
        painter.drawEllipse(rect.adjusted(-8, -8, 8, 8))
        CyberShockwaveRing.draw(
            painter,
            center,
            max(PIXEL_SIZE * 2, wave_radius),
            _with_alpha(accent, 55),
        )

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
        painter.fillRect(
            wr, _with_alpha(COLOR_WHITE, int(190 * intensity))
        )

        center = wr.center()
        radius = snap_pixel(
            int(max(wr.width(), wr.height()) * 0.9 * flash_p)
        )
        if radius > PIXEL_SIZE * 2:
            CyberShockwaveRing.draw(
                painter,
                center,
                radius,
                _with_alpha(accent, int(190 * intensity)),
            )
            CyberShockwaveRing.draw(
                painter,
                center,
                max(0, radius - PIXEL_SIZE * 8),
                _with_alpha(counter, int(130 * intensity)),
            )

        step = PIXEL_SIZE * 2
        zone = wr.adjusted(
            -PIXEL_SIZE * 24,
            -PIXEL_SIZE * 24,
            PIXEL_SIZE * 24,
            PIXEL_SIZE * 24,
        )
        for y in range(zone.top(), zone.bottom(), step):
            for x in range(zone.left(), zone.right(), step):
                if wr.contains(x, y):
                    continue
                threshold = (
                    BAYER_4X4[(y // step) % 4][(x // step) % 4] / 16.0
                )
                if intensity > threshold:
                    painter.fillRect(
                        x,
                        y,
                        step,
                        step,
                        _with_alpha(accent, int(120 * intensity)),
                    )
