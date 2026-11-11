"""Вспомогательные процедурные отрисовщики кинематографичного интро (Studio Trigger FX)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

from ..ui.theme import get_hud_font
from .transition_base import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
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


def draw_arasaka_bios_terminal(painter: QPainter, rect: QRect, t: float) -> None:
    """Отрисовка ретро-консоли BIOS Arasaka Relic OS с проверкой секторов памяти."""
    painter.save()
    painter.fillRect(rect, COLOR_OBSIDIAN)
    painter.setFont(get_hud_font(10, bold=True))
    painter.setPen(with_alpha(COLOR_WHITE, 240))
    painter.drawText(40, 60, "ARASAKA CORP // SECURE BOOT ROM v4.09.2")
    painter.setFont(get_hud_font(8, bold=False))
    painter.setPen(with_alpha(COLOR_ACID_GREEN, 200))
    painter.drawText(40, 85, "HOST NEURAL-LINK DETECTED: [WIN32_DWM_SUBSTRATE]")

    lines = [
        ("INITIALIZING RELIC BUS (CHIP_ID: 0x9F4C)...", 0.15, "[OK]"),
        ("MAPPING SYNAPTIC REGISTERS 0x0000 - 0x7FFF...", 0.35, "[OK]"),
        ("VERIFYING ENCRYPTED CONTAINER: 'CAPRICORN'...", 0.55, "[OK]"),
        ("AUTHENTICATING SOULKILLER KERNEL SIGNATURE...", 0.75, "[OK]"),
        ("ALLOCATING HIGH-VOLTAGE NEURAL MEMORY...", 0.90, "[IN PROGRESS]"),
    ]
    y = 120
    for text, threshold, status in lines:
        if t >= threshold:
            painter.setPen(with_alpha(COLOR_WHITE, 220))
            painter.drawText(40, y, text)
            status_col = COLOR_ACID_GREEN if status == "[OK]" else COLOR_ELECTRIC_BLUE
            painter.setPen(with_alpha(status_col, 240))
            painter.drawText(560, y, status)
            y += 24

    if int(t * 5.0) % 2 == 0:
        painter.fillRect(40, y + 4, 10, 14, COLOR_ACID_GREEN)
    painter.restore()


def draw_kernel_panic_strobe(painter: QPainter, rect: QRect, t: float, rng: random.Random) -> None:
    """Аварийный стробоскоп и тревожный баннер KERNEL PANIC при переполнении биочипа."""
    painter.save()
    t_phase = t - 1.0
    if int(t_phase * 14.0) % 2 == 0:
        painter.fillRect(rect, with_alpha(COLOR_CRIMSON, 55))

    cx = rect.center().x()
    cy = rect.center().y()
    bw, bh = 680, 110
    bx = cx - bw // 2 + int(rng.uniform(-4, 4))
    by = cy - bh // 2 + int(rng.uniform(-3, 3))

    painter.fillRect(QRect(bx, by, bw, bh), with_alpha(COLOR_OBSIDIAN, 240))
    painter.setPen(QPen(with_alpha(COLOR_CRIMSON, 255), 2.5))
    painter.drawRect(QRect(bx, by, bw, bh))

    painter.setFont(get_hud_font(12, bold=True))
    painter.setPen(with_alpha(COLOR_CRIMSON, 255))
    painter.drawText(bx, by + 40, bw, 30, int(Qt.AlignmentFlag.AlignCenter), "CRITICAL BREACH: SOULKILLER_OVERFLOW")

    painter.setFont(get_hud_font(9, bold=False))
    painter.setPen(with_alpha(COLOR_WHITE, 230))
    painter.drawText(
        bx,
        by + 75,
        bw,
        24,
        int(Qt.AlignmentFlag.AlignCenter),
        "CONTAINMENT PROTOCOL BYPASSED // ENGRAM BREACH IMMINENT",
    )
    painter.restore()


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
    full_text = (
        "«Арасака думала запереть меня в железке? Ха! Теперь твой процессор — "
        "моя игровая площадка. Двигайся, хост, я беру руль!»"
    )
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
