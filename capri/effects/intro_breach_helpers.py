"""Вспомогательные процедурные отрисовщики кинематографичного интро (Studio Trigger FX)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

from ..core.dialogue_manager import get_dialogue_manager
from ..ui.draw_utils import make_chamfer_polygon
from ..ui.theme import get_hud_font
from .transition_base import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    with_alpha,
)


@dataclass
class CyberErrorCard:
    """Модель диалогового окна системной ошибки кибердеки/стека."""

    title: str
    code: str
    message: str
    rect: QRect
    spawn_time: float
    border_color: QColor
    vel_x: float = 0.0
    vel_y: float = 0.0
    glitch_offset: float = 0.0


def draw_cyber_error_card(
    painter: QPainter,
    card: CyberErrorCard,
    progress: float,
    glitch_power: float = 0.0,
    rng: random.Random | None = None,
) -> None:
    """Отрисовка стилизованного 45° chamfer окна ошибки с глитчем."""
    if progress <= 0.0:
        return

    r = card.rect
    gx = 0.0
    gy = 0.0
    if glitch_power > 0.0 and rng is not None:
        gx = rng.uniform(-14.0, 14.0) * glitch_power
        gy = rng.uniform(-6.0, 6.0) * glitch_power

    cur_rect = QRect(int(r.x() + gx), int(r.y() + gy), r.width(), r.height())
    alpha_val = int(255 * min(1.0, progress))
    if glitch_power > 0.8:
        alpha_val = int(alpha_val * (1.0 - (glitch_power - 0.8) * 4.0))
        if alpha_val <= 0:
            return

    painter.save()

    # Хроматический сдвиг при сильном глитче
    if glitch_power > 0.35 and rng is not None:
        rgb_rect = QRect(cur_rect.x() + int(rng.uniform(-6, 6)), cur_rect.y(), cur_rect.width(), cur_rect.height())
        poly_rgb = make_chamfer_polygon(rgb_rect, cut=8)
        painter.setPen(QPen(with_alpha(COLOR_VIOLET, int(alpha_val * 0.7)), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(poly_rgb)

    # Основное тело карточки с очертаниями (рамкой) цвета Neon Crimson
    poly = make_chamfer_polygon(cur_rect, cut=8)
    painter.setPen(QPen(with_alpha(COLOR_CRIMSON, alpha_val), 1.8))
    painter.setBrush(with_alpha(COLOR_OBSIDIAN, int(alpha_val * 0.94)))
    painter.drawPolygon(poly)

    # Верхняя плашка заголовка (всегда акцентный красный Neon Crimson)
    header_h = 24
    header_rect = QRect(cur_rect.x(), cur_rect.y(), cur_rect.width(), header_h)
    painter.fillRect(header_rect, with_alpha(COLOR_CRIMSON, int(alpha_val * 0.75)))

    # Заголовок и код ошибки
    painter.setFont(get_hud_font(9, bold=True))
    painter.setPen(with_alpha(COLOR_WHITE, alpha_val))
    painter.drawText(cur_rect.x() + 10, cur_rect.y() + 17, card.title)

    painter.setFont(get_hud_font(8, bold=True))
    painter.setPen(with_alpha(COLOR_WHITE, int(alpha_val * 0.9)))
    painter.drawText(
        cur_rect.x(),
        cur_rect.y() + 4,
        cur_rect.width() - 10,
        18,
        int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
        card.code,
    )

    # Текст сообщения об ошибке
    painter.setFont(get_hud_font(8, bold=False))
    painter.setPen(with_alpha(COLOR_WHITE, int(alpha_val * 0.9)))
    painter.drawText(
        cur_rect.x() + 10,
        cur_rect.y() + 32,
        cur_rect.width() - 20,
        cur_rect.height() - 36,
        int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
        card.message,
    )

    painter.restore()


def draw_glitch_slice(
    painter: QPainter,
    screen_rect: QRect,
    slice_y: int,
    height: int,
    offset_x: int,
) -> None:
    """Горизонтальный строчный срез глитча по экрану."""
    painter.save()
    target_rect = QRect(screen_rect.x(), slice_y, screen_rect.width(), height)
    painter.fillRect(target_rect, with_alpha(COLOR_CRIMSON, 45))
    painter.setPen(QPen(with_alpha(COLOR_WHITE, 120), 1.0))
    painter.drawLine(screen_rect.x(), slice_y, screen_rect.right(), slice_y)
    painter.restore()


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
    full_text = get_dialogue_manager().cinematics.intro_quote
    shown_text = full_text[:max(0, min(len(full_text), typewriter_len))]

    box_w = 640
    box_h = 92
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

    # Заголовок баннера с глитч-глифом
    painter.setFont(get_hud_font(9, bold=True))
    painter.setPen(with_alpha(COLOR_WHITE, int(255 * master_alpha)))
    painter.drawText(rx + 16, ry + 24, "◈ ARASAKA RELIC // BIOCHIP HIJACKED // CAPRI OVERDRIVE")

    # Текст реплики с автопереносом и терминальным курсором
    painter.setFont(get_hud_font(9, bold=False))
    painter.setPen(with_alpha(COLOR_ACID_GREEN, int(245 * master_alpha)))
    cursor = " █" if (int(typewriter_len) % 2 == 0) else ""
    text_rect = QRect(rx + 16, ry + 32, box_w - 32, box_h - 38)
    painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap), shown_text + cursor)

    painter.restore()
