"""Полноэкранный оверлей электрической привязи (молнии) к цели."""

from __future__ import annotations

import contextlib
import math
import random
import time

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from capri.ui.theme import get_hud_font

from ..ui.speech_sfx import get_speech_sfx
from .transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
    PIXEL_SIZE,
    CyberKiroshiReticle,
    CyberPixelBolt,
    CyberPixelSpark,
    with_alpha,
)


def get_virtual_screen_geometry() -> QRect:

    screens = QGuiApplication.screens()
    if not screens:
        return QRect(0, 0, 1920, 1080)
    rect = screens[0].geometry()
    for scr in screens[1:]:
        rect = rect.united(scr.geometry())
    return rect


class LightningTetherOverlay(QWidget):
    """Оверлей анимированных разрядов молнии, связывающих питомца с целевой точкой."""

    def __init__(self, parent: QWidget | None = None) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._start_pos = QPoint(0, 0)
        self._target_pos = QPoint(0, 0)
        self._origin_rect = QRect(0, 0, 0, 0)

        self._bolts: list[CyberPixelBolt] = []
        self._sparks: list[CyberPixelSpark] = []
        self._tick_count = 0
        self._start_time = 0.0

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(20)
        self._anim_timer.timeout.connect(self._on_tick)

        self._sfx_timer = QTimer(self)
        self._sfx_timer.setInterval(110)
        self._sfx_timer.timeout.connect(self._on_sfx_tick)

    def activate(
        self,
        start_pos: QPoint,
        target_pos: QPoint,
        origin_rect: QRect | None = None,
    ) -> None:

        geo = get_virtual_screen_geometry()
        self.setGeometry(geo)

        self._start_pos = start_pos
        self._target_pos = target_pos
        self._origin_rect = origin_rect or QRect(
            start_pos.x() - 40, start_pos.y() - 40, 80, 80
        )
        self._tick_count = 0
        self._start_time = time.monotonic()
        self._sparks.clear()

        self._rebuild_bolts()

        self.raise_()
        self.show()
        self._anim_timer.start()
        self._sfx_timer.start()
        with contextlib.suppress(Exception):
            get_speech_sfx().play_lightning_zap()
        self.update()

    def update_target(self, target_pos: QPoint) -> None:

        if self._target_pos != target_pos:
            self._target_pos = target_pos
            self._rebuild_bolts()
            self.update()

    def update_start(
        self, start_pos: QPoint, origin_rect: QRect | None = None
    ) -> None:

        self._start_pos = start_pos
        if origin_rect is not None:
            self._origin_rect = origin_rect
        self._rebuild_bolts()
        self.update()

    def deactivate(self) -> None:

        self._anim_timer.stop()
        self._sfx_timer.stop()
        self.hide()
        self._bolts.clear()
        self._sparks.clear()

    def _rebuild_bolts(self) -> None:
        offset = self.geometry().topLeft()
        local_start = self._start_pos - offset
        local_target = self._target_pos - offset

        self._bolts.clear()

        dx = local_target.x() - local_start.x()
        dy = local_target.y() - local_start.y()
        dist = math.hypot(dx, dy)
        if dist < 8:
            return

        tension = min(1.0, dist / 800.0)
        branch_rate = 0.28 + 0.35 * tension

        self._bolts.append(
            CyberPixelBolt(
                local_start,
                local_target,
                branch_chance=branch_rate,
            )
        )

        if dist > 35:
            jitter_start = local_start + QPoint(
                random.randint(-14, 14), random.randint(-14, 14)
            )
            jitter_target = local_target + QPoint(
                random.randint(-10, 10), random.randint(-10, 10)
            )
            self._bolts.append(
                CyberPixelBolt(
                    jitter_start,
                    jitter_target,
                    branch_chance=min(0.65, branch_rate + 0.1),
                )
            )

        if dist > 250 or tension > 0.4:
            arc_start = local_start + QPoint(
                random.randint(-8, 8), random.randint(-8, 8)
            )
            arc_target = local_target + QPoint(
                random.randint(-12, 12), random.randint(-12, 12)
            )
            self._bolts.append(
                CyberPixelBolt(
                    arc_start,
                    arc_target,
                    branch_chance=0.45,
                )
            )

    def _on_tick(self) -> None:
        self._tick_count += 1
        offset = self.geometry().topLeft()
        local_target = self._target_pos - offset

        for bolt in self._bolts:
            bolt.jitter()

        if random.random() < 0.65:
            angle = random.uniform(0, math.tau)
            speed = random.uniform(40.0, 160.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            kind = random.choice(("spark", "bit", "bar"))
            self._sparks.append(
                CyberPixelSpark(
                    local_target.x(),
                    local_target.y(),
                    vx,
                    vy,
                    color=random.choice(
                        (COLOR_CRIMSON, COLOR_WHITE, COLOR_ACID_GREEN)
                    ),
                    size=PIXEL_SIZE,
                    life=random.uniform(0.15, 0.40),
                    kind=kind,
                )
            )

        dt = 0.02
        self._sparks = [s for s in self._sparks if s.step(dt)]

        self.update()

    def _on_sfx_tick(self) -> None:
        if random.random() < 0.45:
            with contextlib.suppress(Exception):
                get_speech_sfx().play_lightning_zap()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        offset = self.geometry().topLeft()
        local_start = self._start_pos - offset
        local_target = self._target_pos - offset

        for bolt in self._bolts:
            bolt.draw(painter, progress=1.0)

        for spark in self._sparks:
            spark.draw(painter)

        reticle_size = 64
        reticle_rect = QRect(
            local_target.x() - reticle_size // 2,
            local_target.y() - reticle_size // 2,
            reticle_size,
            reticle_size,
        )
        elapsed = time.monotonic() - self._start_time
        dx = self._target_pos.x() - self._start_pos.x()
        dy = self._target_pos.y() - self._start_pos.y()
        dist = int(math.hypot(dx, dy))
        tension = min(1.0, dist / 800.0)

        rotation = elapsed * math.tau * (1.2 + tension * 2.5)

        if tension > 0.65:
            hud_label = "BLACKWALL // BREACH"
        elif tension > 0.35:
            hud_label = "OVERDRIVE // OVERLOAD"
        else:
            hud_label = "CYBER // LEASH_LOCK"

        CyberKiroshiReticle.draw(
            painter,
            reticle_rect,
            progress=1.0,
            color=COLOR_CRIMSON,
            bracket_offset=int(
                abs(math.sin(elapsed * (8.0 + tension * 12.0)))
                * (6 + int(tension * 6))
            ),
            rotation=rotation,
            label=hud_label,
            locked=True,
        )

        font = get_hud_font(10, bold=True)
        painter.setFont(font)

        tag = f"TENS: {int(tension * 100)}% // DISP:[{dx:+04d},{dy:+04d}] // VOLT:0x{(min(9999, int(dist * 12.5))):04X}"
        tag_rect = QRect(
            local_target.x() + 38, local_target.y() - 8, 255, 16
        )
        painter.fillRect(tag_rect, with_alpha(COLOR_OBSIDIAN, 230))
        painter.setPen(QPen(COLOR_CRIMSON, 1))
        painter.drawRect(tag_rect)
        painter.setPen(COLOR_WHITE)
        painter.drawText(
            tag_rect.adjusted(4, 0, 0, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            tag,
        )

        if dist > 80:
            hex_samples = (
                "0xDEAD",
                "0xBEEF",
                "BREACH",
                "0x00FF",
                "NULL_PTR",
                "CORRUPT",
            )
            rng_hex = random.Random(int(elapsed * 15) % 1000)
            for step_ratio in (0.3, 0.6, 0.85):
                hx = int(
                    local_start.x()
                    + (local_target.x() - local_start.x()) * step_ratio
                )
                hy = int(
                    local_start.y()
                    + (local_target.y() - local_start.y()) * step_ratio
                )
                glyph = rng_hex.choice(hex_samples)
                glyph_rect = QRect(
                    hx + rng_hex.randint(-16, 16),
                    hy + rng_hex.randint(-16, 16),
                    56,
                    12,
                )
                painter.fillRect(
                    glyph_rect, with_alpha(COLOR_OBSIDIAN, 190)
                )
                painter.setPen(
                    with_alpha(COLOR_CRIMSON, rng_hex.randint(180, 255))
                )
                painter.drawText(
                    glyph_rect, Qt.AlignmentFlag.AlignCenter, glyph
                )

        anchor_rect = QRect(
            local_start.x() - 6, local_start.y() - 6, 12, 12
        )
        painter.setPen(QPen(COLOR_ACID_GREEN, 1))
        painter.drawRect(anchor_rect)
        painter.drawLine(
            local_start.x() - 10,
            local_start.y(),
            local_start.x() + 10,
            local_start.y(),
        )
        painter.drawLine(
            local_start.x(),
            local_start.y() - 10,
            local_start.x(),
            local_start.y() + 10,
        )

        painter.end()
