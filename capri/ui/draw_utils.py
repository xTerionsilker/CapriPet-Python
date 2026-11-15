"""Утилиты процедурной отрисовки: пиксельное квантование, 45° chamfer и сканлайны."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygon

PIXEL_SIZE = 4


def snap_pixel(val: float, step: int = PIXEL_SIZE) -> int:
    """Выравнивает координату по пиксельной сетке."""
    return round(val / step) * step


def snap_point(pt: QPoint, step: int = PIXEL_SIZE) -> QPoint:
    """Выравнивает точку по пиксельной сетке."""
    return QPoint(snap_pixel(pt.x(), step), snap_pixel(pt.y(), step))


def with_alpha(color: QColor | str, alpha: int) -> QColor:
    """Возвращает копию цвета с установленной альфа-прозрачностью (0..255)."""
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c


def make_chamfer_path(rect: QRect | QRectF, cut: float) -> QPainterPath:
    """Генерирует контур QPainterPath со скошенными под 45 градусов углами."""
    left, top = rect.left(), rect.top()
    right, bottom = rect.right(), rect.bottom()
    path = QPainterPath()
    path.moveTo(left + cut, top)
    path.lineTo(right - cut, top)
    path.lineTo(right, top + cut)
    path.lineTo(right, bottom - cut)
    path.lineTo(right - cut, bottom)
    path.lineTo(left + cut, bottom)
    path.lineTo(left, bottom - cut)
    path.lineTo(left, top + cut)
    path.closeSubpath()
    return path


def make_chamfer_polygon(rect: QRect, cut: int) -> QPolygon:
    """Генерирует QPolygon со скошенными под 45 градусов углами."""
    left, top = rect.left(), rect.top()
    right, bottom = rect.right(), rect.bottom()
    return QPolygon(
        [
            QPoint(left + cut, top),
            QPoint(right - cut, top),
            QPoint(right, top + cut),
            QPoint(right, bottom - cut),
            QPoint(right - cut, bottom),
            QPoint(left + cut, bottom),
            QPoint(left, bottom - cut),
            QPoint(left, top + cut),
        ]
    )


def draw_scanlines(
    painter: QPainter,
    rect: QRect | QRectF,
    spacing: int = 3,
    alpha: int = 15,
    color: QColor | str = "#126EE9",
) -> None:
    """Отрисовывает горизонтальные сканлайны CRT внутри заданного прямоугольника."""
    w, h = int(rect.width()), int(rect.height())
    if w <= 0 or h <= 0:
        return
    left = int(rect.left())
    top = int(rect.top())
    pen = QPen(with_alpha(color, alpha), 1)
    painter.save()
    painter.setPen(pen)
    for y in range(top, top + h, spacing):
        painter.drawLine(left, y, left + w, y)
    painter.restore()
