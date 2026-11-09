"""Вспомогательные процедурные отрисовщики кинематографичного интро (Studio Trigger FX)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF

from ..ui.theme import get_hud_font
from .transition_base import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    PIXEL_SIZE,
    snap_pixel,
    with_alpha,
)


@dataclass
class GlassShard:
    """Полигональный осколок разбитого стекла с вращением и физикой падения."""

    poly: list[QPointF]
    x: float
    y: float
    vx: float
    vy: float
    rot: float
    v_rot: float
    scale: float
    alpha: float
    color: QColor

    def update(self, dt: float) -> None:
        self.vy += 950.0 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rot += self.v_rot * dt
        self.alpha = max(0.0, self.alpha - 0.38 * dt)

    def draw(self, painter: QPainter, master_alpha: float) -> None:
        if self.alpha <= 0.01 or master_alpha <= 0.01:
            return
        painter.save()
        painter.translate(self.x, self.y)
        painter.rotate(self.rot)
        painter.scale(self.scale, self.scale)

        total_a = max(0.0, min(1.0, self.alpha * master_alpha))
        # Полупрозрачная граненая подложка стекла
        fill_col = with_alpha(self.color, int(85 * total_a))
        border_col = with_alpha(COLOR_WHITE, int(240 * total_a))
        rim_col = with_alpha(COLOR_CRIMSON, int(190 * total_a))

        poly_f = QPolygonF(self.poly)
        painter.setPen(QPen(rim_col, 2.0))
        painter.setBrush(fill_col)
        painter.drawPolygon(poly_f)

        # Яркая грань кристалла стекла
        painter.setPen(QPen(border_col, 1.2))
        if len(self.poly) >= 2:
            painter.drawLine(self.poly[0], self.poly[1])

        painter.restore()


@dataclass
class SpeedLine:
    """Кинетическая экшен-линия движения в стиле Studio Trigger."""

    angle: float
    length: float
    dist: float
    width: float
    color: QColor

    def draw(self, painter: QPainter, center: QPointF, progress: float, master_alpha: float) -> None:
        if master_alpha <= 0.01:
            return
        cx, cy = center.x(), center.y()
        d = self.dist * progress
        p1_x = cx + d * math.cos(self.angle)
        p1_y = cy + d * math.sin(self.angle)
        p2_x = cx + (d + self.length) * math.cos(self.angle)
        p2_y = cy + (d + self.length) * math.sin(self.angle)

        pen = QPen(with_alpha(self.color, int(220 * master_alpha)), self.width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(p1_x, p1_y), QPointF(p2_x, p2_y))


def draw_cyber_reticle(painter: QPainter, center: QPointF, t: float, max_t: float) -> None:
    """Многоуровневый голографический прицел наведения перед ударом."""
    cx, cy = center.x(), center.y()
    p = min(1.0, t / max_t)
    r = 130.0 * (1.0 - p) + 36.0
    rot = t * 140.0

    painter.save()
    painter.translate(cx, cy)
    painter.rotate(rot)

    # Внешнее сегментированное кольцо
    pen_crimson = QPen(with_alpha(COLOR_CRIMSON, int(230 * p)), 2.5)
    painter.setPen(pen_crimson)
    painter.drawArc(int(-r), int(-r), int(2 * r), int(2 * r), 30 * 16, 60 * 16)
    painter.drawArc(int(-r), int(-r), int(2 * r), int(2 * r), 120 * 16, 60 * 16)
    painter.drawArc(int(-r), int(-r), int(2 * r), int(2 * r), 210 * 16, 60 * 16)
    painter.drawArc(int(-r), int(-r), int(2 * r), int(2 * r), 300 * 16, 60 * 16)

    # Внутренний прицел с обратным вращением
    painter.rotate(-2.0 * rot)
    pen_green = QPen(with_alpha(COLOR_ACID_GREEN, int(240 * p)), 1.5)
    painter.setPen(pen_green)
    inner_r = r * 0.45
    painter.drawLine(QPointF(-inner_r - 12, 0), QPointF(inner_r + 12, 0))
    painter.drawLine(QPointF(0, -inner_r - 12), QPointF(0, inner_r + 12))

    painter.restore()

    # Текстовый маркер захвата цели
    painter.setFont(get_hud_font(9, bold=True))
    painter.setPen(with_alpha(COLOR_WHITE, int(220 * p)))
    painter.drawText(
        QRect(int(cx - 150), int(cy + r + 14), 300, 24),
        Qt.AlignmentFlag.AlignCenter,
        "LOCK: [SOULKILLER_CORE // LEVEL_9]",
    )


def draw_breach_lightning(
    painter: QPainter,
    hole_polygon: QPolygonF,
    rng: random.Random,
    alpha: float,
) -> None:
    """Электрические разряды Blackwall, пляшущие по контуру разлома стекла."""
    if alpha <= 0.05 or hole_polygon.count() < 3:
        return

    pts = [hole_polygon.at(i) for i in range(hole_polygon.count())]
    num_arcs = min(6, len(pts))
    painter.save()

    for _ in range(num_arcs):
        idx = rng.randint(0, len(pts) - 1)
        next_idx = (idx + rng.randint(1, 3)) % len(pts)
        p1 = pts[idx]
        p2 = pts[next_idx]

        # Создание ломаного разряда между вершинами
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < 15:
            continue

        steps = 4
        prev = p1
        bolt_pts = [prev]
        for step_i in range(1, steps):
            ratio = step_i / steps
            mx = p1.x() + dx * ratio
            my = p1.y() + dy * ratio
            nx = -dy / dist
            ny = dx / dist
            jitter = rng.uniform(-18.0, 18.0)
            bolt_pts.append(QPointF(mx + nx * jitter, my + ny * jitter))
        bolt_pts.append(p2)

        # Отрисовка ореола и ядра молнии
        painter.setPen(QPen(with_alpha(COLOR_CRIMSON, int(180 * alpha)), 3.0))
        for j in range(len(bolt_pts) - 1):
            painter.drawLine(bolt_pts[j], bolt_pts[j + 1])

        painter.setPen(QPen(with_alpha(COLOR_WHITE, int(255 * alpha)), 1.2))
        for j in range(len(bolt_pts) - 1):
            painter.drawLine(bolt_pts[j], bolt_pts[j + 1])

    painter.restore()


def draw_dialogue_cyber_hud(
    painter: QPainter,
    bx: int,
    by: int,
    master_alpha: float,
    typewriter_len: int,
) -> None:
    """Высокотехнологичный диалоговый HUD-баннер со скошенными углами 45° и hazard-баром."""
    full_text = "«Ха! Твой экран слишком хрупкий для меня, мясной!»"
    shown_text = full_text[:max(0, min(len(full_text), typewriter_len))]

    box_w = 480
    box_h = 76
    rx = bx - box_w // 2
    ry = by

    painter.save()
    # 45-градусные фаски корпуса
    chamfer = 12.0
    path = QPainterPath()
    path.moveTo(rx + chamfer, ry)
    path.lineTo(rx + box_w, ry)
    path.lineTo(rx + box_w, ry + box_h - chamfer)
    path.lineTo(rx + box_w - chamfer, ry + box_h)
    path.lineTo(rx, ry + box_h)
    path.lineTo(rx, ry + chamfer)
    path.closeSubpath()

    painter.fillPath(path, with_alpha(COLOR_OBSIDIAN, int(235 * master_alpha)))
    painter.setPen(QPen(with_alpha(COLOR_CRIMSON, int(255 * master_alpha)), 2.0))
    painter.drawPath(path)

    # Верхняя полоса опасности (Hazard Stripes)
    hazard_w = box_w - 24
    for hx in range(rx + 16, rx + hazard_w, 14):
        painter.setPen(QPen(with_alpha(COLOR_CRIMSON, int(140 * master_alpha)), 2.0))
        painter.drawLine(hx, ry + 4, hx + 6, ry + 10)

    # Заголовок баннера
    painter.setFont(get_hud_font(10, bold=True))
    painter.setPen(with_alpha(COLOR_WHITE, int(255 * master_alpha)))
    painter.drawText(rx + 16, ry + 26, "PROJECT CAPRICORN // BIOCHIP RECALL")

    # Текст реплики с мигающим терминальным курсором
    painter.setFont(get_hud_font(10, bold=False))
    painter.setPen(with_alpha(COLOR_ACID_GREEN, int(240 * master_alpha)))
    cursor = " █" if (int(typewriter_len) % 2 == 0) else ""
    painter.drawText(rx + 16, ry + 54, shown_text + cursor)

    painter.restore()
