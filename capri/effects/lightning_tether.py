"""Полноэкранный оверлей электрической привязи (молнии) к цели."""

from __future__ import annotations

import contextlib
import math
import random
import time
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from capri.ui.theme import get_hud_font

from ..audio.sfx_player import get_speech_sfx
from .transition_fx import (
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    CyberPixelSpark,
    CyberTriggerCrosshair,
    CyberVectorBolt,
    with_alpha,
)

_VIRUS_WORDS: tuple[str, ...] = (
    "0xDEAD",
    "VIRUS",
    "CORRUPT",
    "0xFE",
    "BIOCHIP",
    "BREACH",
    "INFEST",
    "NULL",
    "SOULKILLER",
    "ERR_0x00",
)


@dataclass
class _VirusSpore:
    x: float
    y: float
    vx: float
    vy: float
    text: str
    life: float
    max_life: float
    color: QColor

    def step(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0.0

    def draw(self, painter: QPainter, font: QFont) -> None:
        if self.life <= 0.0:
            return
        alpha = int(240 * (self.life / self.max_life))
        painter.setFont(font)
        painter.setPen(with_alpha(self.color, alpha))
        painter.drawText(int(self.x), int(self.y), self.text)


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
        self._spores: list[_VirusSpore] = []
        self._spore_font: QFont = get_hud_font(8, bold=True)
        self._start_time = 0.0
        self._is_fizzling: bool = False
        self._fizzle_start: float = 0.0
        self._fizzle_duration: float = 0.20
        self._current_tension: float = 0.0

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
        self._is_fizzling = False
        self._sparks.clear()
        self._spores.clear()

        self._rebuild_bolts()

        self.raise_()
        self.show()
        self._anim_timer.start()
        self._sfx_timer.start()
        with contextlib.suppress(Exception):
            get_speech_sfx().play_lightning_zap()
        self.update()

    def update_target(self, target_pos: QPoint) -> None:
        if self._is_fizzling:
            return
        if self._target_pos != target_pos:
            self._target_pos = target_pos
            self._rebuild_bolts()
            self.update()

    def update_start(
        self, start_pos: QPoint, origin_rect: QRect | None = None
    ) -> None:
        if self._is_fizzling:
            return
        self._start_pos = start_pos
        self._rebuild_bolts()
        self.update()

    def start_fizzle(self) -> None:
        """Плавный распад молнии на затухающие искры при отмене."""
        if not self.isVisible() or self._is_fizzling:
            return
        self._is_fizzling = True
        self._fizzle_start = time.monotonic()
        self._sfx_timer.stop()

        for bolt in self._bolts:
            for pt in bolt.spine_points:
                ang = random.uniform(0, math.tau)
                spd = random.uniform(40.0, 180.0)
                self._sparks.append(
                    CyberPixelSpark(
                        pt.x(),
                        pt.y(),
                        math.cos(ang) * spd,
                        math.sin(ang) * spd,
                        life=random.uniform(0.12, 0.25),
                    )
                )
        self.update()

    def deactivate(self) -> None:
        self._is_fizzling = False
        self._anim_timer.stop()
        self._sfx_timer.stop()
        self.hide()
        self._bolts.clear()
        self._sparks.clear()
        self._spores.clear()

    def _rebuild_bolts(self) -> None:
        if self._is_fizzling:
            return
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
        self._current_tension = tension
        base_w = 16.0 + 10.0 * tension

        # Прогрессивное ветвление и толщина в стиле Studio Trigger
        branch_chance = 0.15 + 0.35 * tension
        bolt = CyberVectorBolt(
            local_start,
            local_target,
            base_width=base_w,
            tip_width=2.5,
            branch_chance=branch_chance,
            color=COLOR_CRIMSON,
        )
        bolt.set_tension(tension)
        self._bolts.append(bolt)

        adaptive_interval = max(35, int(110 - 70 * tension))
        if self._sfx_timer.interval() != adaptive_interval:
            self._sfx_timer.setInterval(adaptive_interval)

    def _on_tick(self) -> None:
        if self._is_fizzling:
            now = time.monotonic()
            if now - self._fizzle_start >= self._fizzle_duration:
                self.deactivate()
                return

        for bolt in self._bolts:
            bolt.jitter(force=(self._current_tension > 0.65))

        if not self._is_fizzling and self._bolts:
            for bolt in self._bolts:
                if bolt.spine_points and random.random() < (0.35 + 0.50 * self._current_tension):
                    pt = random.choice(bolt.spine_points)
                    ang = random.uniform(0, math.tau)
                    spd = random.uniform(50.0, 220.0)
                    self._sparks.append(
                        CyberPixelSpark(
                            pt.x(),
                            pt.y(),
                            math.cos(ang) * spd,
                            math.sin(ang) * spd,
                            life=random.uniform(0.10, 0.22),
                        )
                    )

        dt = 0.02
        self._sparks = [s for s in self._sparks if s.step(dt)]
        self._spores = [sp for sp in self._spores if sp.step(dt)]

        # Генерация вирусных спор / обрывков поврежденного кода
        if not self._is_fizzling and self._bolts and random.random() < (0.35 + 0.45 * self._current_tension):
            bolt = random.choice(self._bolts)
            if bolt.spine_points:
                pt = random.choice(bolt.spine_points)
                vx = random.uniform(-40.0, 40.0)
                vy = random.uniform(-40.0, 40.0)
                w = random.choice(_VIRUS_WORDS)
                col = random.choice((COLOR_CRIMSON, COLOR_WHITE, COLOR_VIOLET))
                life = random.uniform(0.20, 0.45)
                self._spores.append(
                    _VirusSpore(
                        pt.x() + random.uniform(-12, 12),
                        pt.y() + random.uniform(-12, 12),
                        vx,
                        vy,
                        w,
                        life,
                        life,
                        col,
                    )
                )

        self.update()

    def _on_sfx_tick(self) -> None:
        chance = 0.45 + 0.40 * self._current_tension
        if random.random() < chance:
            with contextlib.suppress(Exception):
                get_speech_sfx().play_lightning_zap()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        now = time.monotonic()
        progress = (
            max(0.0, 1.0 - (now - self._fizzle_start) / self._fizzle_duration)
            if self._is_fizzling
            else 1.0
        )

        offset = self.geometry().topLeft()
        local_start = self._start_pos - offset
        local_target = self._target_pos - offset

        for bolt in self._bolts:
            bolt.draw(painter, progress=progress)

        for spark in self._sparks:
            spark.draw(painter)

        for spore in self._spores:
            spore.draw(painter, self._spore_font)

        if self._is_fizzling:
            painter.end()
            return

        elapsed = now - self._start_time
        dx = self._target_pos.x() - self._start_pos.x()
        dy = self._target_pos.y() - self._start_pos.y()
        dist = int(math.hypot(dx, dy))
        tension = min(1.0, dist / 800.0)

        rotation = elapsed * math.tau * (1.2 + tension * 2.5)

        # Вирусные капилляры заражения (Infection Veins)
        num_veins = 8
        for v_i in range(num_veins):
            base_angle = (v_i / num_veins) * math.tau + elapsed * 1.4
            v_len = (24.0 + 40.0 * tension) * (0.8 + 0.4 * ((v_i * 3) % 5) / 5.0)
            curr_pt = QPointF(local_target)
            vein_pts = [curr_pt]
            for seg in range(1, 4):
                seg_r = seg / 3.0
                ang = base_angle + ((v_i % 2) * 2 - 1) * (0.35 * seg)
                next_x = float(local_target.x()) + math.cos(ang) * (v_len * seg_r)
                next_y = float(local_target.y()) + math.sin(ang) * (v_len * seg_r)
                vein_pts.append(QPointF(next_x, next_y))
            v_pen = QPen(with_alpha(COLOR_CRIMSON, int(220 * progress)), 1.5)
            painter.setPen(v_pen)
            for s in range(len(vein_pts) - 1):
                painter.drawLine(vein_pts[s], vein_pts[s + 1])

        CyberTriggerCrosshair.draw(
            painter,
            local_target,
            progress=1.0,
            color=COLOR_CRIMSON,
            tension=tension,
            rotation=rotation,
        )

        # Бегущие энергетические ромбические импульсы вдоль ствола молнии
        if dist > 30:
            for ring_i in range(3):
                ring_phase = (elapsed * (1.8 + tension * 2.5) + ring_i / 3.0) % 1.0
                ring_x = local_start.x() + (local_target.x() - local_start.x()) * ring_phase
                ring_y = local_start.y() + (local_target.y() - local_start.y()) * ring_phase
                r_size = 4.0 + 3.0 * (1.0 - ring_phase) + 3.0 * tension
                r_pts = [
                    QPointF(ring_x, ring_y - r_size),
                    QPointF(ring_x + r_size, ring_y),
                    QPointF(ring_x, ring_y + r_size),
                    QPointF(ring_x - r_size, ring_y),
                ]
                painter.setPen(QPen(with_alpha(COLOR_WHITE, int(220 * ring_phase)), 1.5))
                painter.setBrush(with_alpha(COLOR_CRIMSON, int(180 * ring_phase)))
                painter.drawPolygon(QPolygonF(r_pts))

        font = get_hud_font(9, bold=True)
        painter.setFont(font)

        tag_top = f"[!] BLACKWALL VIRUS // INFECTION: {int(tension * 100)}%"
        tag_sub = f"CORRUPT // DISP:[{dx:+04d},{dy:+04d}] // OVERRIDE:0x{(min(9999, int(dist * 12.5))):04X}"
        tag_rect = QRect(local_target.x() + 42, local_target.y() - 14, 280, 28)
        painter.fillRect(tag_rect, with_alpha(COLOR_OBSIDIAN, 240))
        painter.setPen(QPen(COLOR_CRIMSON, 1.5))
        painter.drawRect(tag_rect)
        painter.setPen(QPen(COLOR_WHITE, 1))
        painter.drawRect(tag_rect.adjusted(2, 2, -2, -2))
        painter.setPen(COLOR_CRIMSON)
        painter.drawText(
            tag_rect.adjusted(6, 2, 0, -14),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            tag_top,
        )
        painter.setPen(COLOR_WHITE)
        painter.drawText(
            tag_rect.adjusted(6, 14, 0, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            tag_sub,
        )

        anchor_rect = QRect(local_start.x() - 10, local_start.y() - 10, 20, 20)
        painter.setPen(QPen(with_alpha(COLOR_CRIMSON, 230), 1.5))
        painter.drawRect(anchor_rect)
        painter.setPen(QPen(COLOR_WHITE, 1))
        painter.drawRect(anchor_rect.adjusted(3, 3, -3, -3))
        for ox, oy in ((-14, 0), (14, 0), (0, -14), (0, 14)):
            painter.setPen(QPen(COLOR_CRIMSON, 1.5))
            painter.drawLine(
                local_start.x(),
                local_start.y(),
                local_start.x() + ox,
                local_start.y() + oy,
            )

        painter.end()
