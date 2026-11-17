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

from ..audio.sfx_player import get_speech_sfx
from .transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
    PIXEL_SIZE,
    CyberPixelSpark,
    CyberTriggerCrosshair,
    CyberVectorBolt,
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

    def __init__(self, _parent: QWidget | None = None) -> None:
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

        self._bolts: list[CyberVectorBolt] = []
        self._sparks: list[CyberPixelSpark] = []
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
        base_w = 16.0 + 10.0 * tension

        # Основной векторный луч молнии
        self._bolts.append(
            CyberVectorBolt(
                local_start,
                local_target,
                base_width=base_w,
                tip_width=2.5,
                branch_chance=0.35 + 0.3 * tension,
                color=COLOR_CRIMSON,
            )
        )

        # Дополнительная параллельная искра при сильном натяжении
        if dist > 40:
            jitter_start = local_start + QPoint(
                random.randint(-10, 10), random.randint(-10, 10)
            )
            jitter_target = local_target + QPoint(
                random.randint(-6, 6), random.randint(-6, 6)
            )
            self._bolts.append(
                CyberVectorBolt(
                    jitter_start,
                    jitter_target,
                    base_width=max(4.0, base_w * 0.4),
                    tip_width=1.5,
                    branch_chance=0.2,
                    color=COLOR_CRIMSON,
                )
            )

    def _on_tick(self) -> None:
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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        offset = self.geometry().topLeft()
        local_start = self._start_pos - offset
        local_target = self._target_pos - offset

        for bolt in self._bolts:
            bolt.draw(painter, progress=1.0)

        for spark in self._sparks:
            spark.draw(painter)

        elapsed = time.monotonic() - self._start_time
        dx = self._target_pos.x() - self._start_pos.x()
        dy = self._target_pos.y() - self._start_pos.y()
        dist = int(math.hypot(dx, dy))
        tension = min(1.0, dist / 800.0)

        rotation = elapsed * math.tau * (1.2 + tension * 2.5)

        CyberTriggerCrosshair.draw(
            painter,
            local_target,
            progress=1.0,
            color=COLOR_CRIMSON,
            tension=tension,
            rotation=rotation,
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
