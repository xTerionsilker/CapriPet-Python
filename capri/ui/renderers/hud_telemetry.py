"""HUD telemetry and target acquisition overlays painter for CapriPet."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from PySide6.QtGui import QColor, QPainter, QPen

from ...effects.transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    snap_pixel,
)
from ..theme import get_hud_font

if TYPE_CHECKING:
    from ..pet_renderer import PetRenderState


class HudTelemetryPainter:
    """Отрисовка оверлеев телеметрии HUD и захвата цели Blackwall."""

    @staticmethod
    def get_telemetry_tag(state: PetRenderState) -> str:
        if state.is_consuming:
            return "[CONSUME//BLACKWALL]"
        if state.is_target_acquired:
            return "[CONSUME_TARGET_ACQUIRED]"
        if state.is_dragging:
            return "[DRAG//RELOCATE]"
        if state.is_speaking:
            return "[TX//SPEAKING]"
        if state.is_pose_transition:
            return "[REBUILD//0x1A]"
        return state.telemetry_tag

    @classmethod
    def draw_telemetry(
        cls,
        painter: QPainter,
        w: int,
        h: int,
        severity: float,
        state: PetRenderState,
    ) -> None:
        if (
            severity > 0.4
            or state.is_speaking
            or state.is_dragging
            or state.is_target_acquired
            or state.is_consuming
        ):
            font = get_hud_font(9, bold=True)
            painter.setFont(font)

            tag = cls.get_telemetry_tag(state)
            tag_w = len(tag) * 6 + 6
            tag_h = 10
            tag_x = snap_pixel(w - tag_w - 4)
            tag_y = snap_pixel(h - 14)
            painter.fillRect(
                tag_x,
                tag_y,
                tag_w,
                tag_h,
                QColor(
                    COLOR_OBSIDIAN.red(),
                    COLOR_OBSIDIAN.green(),
                    COLOR_OBSIDIAN.blue(),
                    210,
                ),
            )
            painter.drawRect(tag_x, tag_y, tag_w, tag_h)
            tag_color = (
                COLOR_CRIMSON
                if (severity > 0.7 or state.is_dragging)
                else COLOR_ACID_GREEN
            )
            painter.setPen(tag_color)
            painter.drawText(tag_x + 3, tag_y + 8, tag)

    @staticmethod
    def draw_target_acquired_overlay(
        painter: QPainter,
        w: int,
        h: int,
        state: PetRenderState,
    ) -> None:
        """Render cyberpunk combat lock-on crosshair and Blackwall lightning tendrils."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pen = QPen(COLOR_CRIMSON)
        pen.setWidth(2)
        painter.setPen(pen)

        # Crosshair brackets around sprite
        margin = 6
        arm_len = 16
        # Top-left
        painter.drawLine(margin, margin, margin + arm_len, margin)
        painter.drawLine(margin, margin, margin, margin + arm_len)
        # Top-right
        painter.drawLine(w - margin, margin, w - margin - arm_len, margin)
        painter.drawLine(w - margin, margin, w - margin, margin + arm_len)
        # Bottom-left
        painter.drawLine(margin, h - margin, margin + arm_len, h - margin)
        painter.drawLine(margin, h - margin, margin, h - margin - arm_len)
        # Bottom-right
        painter.drawLine(w - margin, h - margin, w - margin - arm_len, h - margin)
        painter.drawLine(w - margin, h - margin, w - margin, h - margin - arm_len)

        # Manhattan path converging lightning discharges towards center
        cx, cy = w // 2, h // 2
        tendril_count = 6 if state.is_consuming else 4
        for _ in range(tendril_count):
            edge = random.choice(("top", "bottom", "left", "right"))
            if edge == "top":
                curr_x, curr_y = random.randint(0, w), 0
            elif edge == "bottom":
                curr_x, curr_y = random.randint(0, w), h
            elif edge == "left":
                curr_x, curr_y = 0, random.randint(0, h)
            else:
                curr_x, curr_y = w, random.randint(0, h)

            l_pen = QPen(
                COLOR_CRIMSON if random.random() < 0.85 else COLOR_ACID_GREEN
            )
            l_pen.setWidth(random.choice((1, 2)))
            painter.setPen(l_pen)

            steps = 4
            for s in range(steps):
                progress = (s + 1) / steps
                tx = int(curr_x + (cx - curr_x) * progress) + random.randint(-8, 8)
                ty = int(curr_y + (cy - curr_y) * progress) + random.randint(-8, 8)
                painter.drawLine(curr_x, curr_y, tx, curr_y)
                painter.drawLine(tx, curr_y, tx, ty)
                curr_x, curr_y = tx, ty
            painter.drawLine(curr_x, curr_y, cx, cy)

        painter.restore()
