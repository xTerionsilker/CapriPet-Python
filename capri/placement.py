"""Случайное размещение окна на экране вне заданного прямоугольника.

Геометрия для облачка речи (``capri.speech``), вынесенная в чистые
функции: экран делится на полосы свободного места вокруг ``blocked``,
в них выбирается случайная точка, а если свободного места нет — точка
с наименьшим перекрытием.

Все прямоугольники — в координатах одного экрана.
"""

from __future__ import annotations

import random

from PySide6.QtCore import QRect

#: Визуальный зазор между облачком и главным окном.
GAP = 24

#: Сколько раз перебирать точку, когда свободного места нет.
OVERLAP_ATTEMPTS = 200


def free_bands(area: QRect, blocked: QRect | None) -> list[QRect]:
    """Полосы экрана ``area``, свободные от ``blocked``.

    Это объединение полос сверху, снизу, слева и справа от заблокированного
    прямоугольника; если его нет, свободен весь экран.
    """
    if blocked is None or blocked.isEmpty():
        return [area]

    bands: list[QRect] = []
    if blocked.top() > area.top():
        bands.append(
            QRect(
                area.left(),
                area.top(),
                area.width(),
                blocked.top() - area.top(),
            )
        )
    if blocked.bottom() < area.bottom():
        bands.append(
            QRect(
                area.left(),
                blocked.bottom() + 1,
                area.width(),
                area.bottom() - blocked.bottom(),
            )
        )
    if blocked.left() > area.left():
        bands.append(
            QRect(
                area.left(),
                area.top(),
                blocked.left() - area.left(),
                area.height(),
            )
        )
    if blocked.right() < area.right():
        bands.append(
            QRect(
                blocked.right() + 1,
                area.top(),
                area.right() - blocked.right(),
                area.height(),
            )
        )
    return bands


def random_free_point(
    bands: list[QRect], width: int, height: int
) -> tuple[int, int] | None:
    """Случайная точка, где окно ``width``×``height`` помещается в полосе.

    Точки взвешиваются по площади, поэтому большие полосы выбираются
    чаще. ``None`` — ни одна полоса не подходит по размеру.
    """
    fitting = [
        band
        for band in bands
        if band.width() >= width and band.height() >= height
    ]
    if not fitting:
        return None

    spans = [
        (band, (band.width() - width + 1) * (band.height() - height + 1))
        for band in fitting
    ]
    choice = random.randrange(sum(span for _, span in spans))
    for band, span in spans:
        if choice < span:
            columns = band.width() - width + 1
            return (
                band.left() + choice % columns,
                band.top() + choice // columns,
            )
        choice -= span
    return None


def least_overlap_point(
    area: QRect, blocked: QRect, width: int, height: int
) -> tuple[int, int]:
    """Точка в ``area`` с наименьшим перекрытием с ``blocked``."""
    max_x = max(area.left(), area.right() - width + 1)
    max_y = max(area.top(), area.bottom() - height + 1)
    best = (area.left(), area.top())
    least_overlap: int | None = None
    for _ in range(OVERLAP_ATTEMPTS):
        x = random.randint(area.left(), max_x)
        y = random.randint(area.top(), max_y)
        overlap = QRect(x, y, width, height).intersected(blocked)
        overlap_area = overlap.width() * overlap.height()
        if least_overlap is None or overlap_area < least_overlap:
            least_overlap = overlap_area
            best = (x, y)
    return best


def pick_position(
    area: QRect, blocked: QRect | None, width: int, height: int
) -> tuple[int, int]:
    """Выбрать точку для окна ``width``×``height`` на экране ``area``.

    Сначала — случайная точка в свободной полосе; если свободного места
    нет вовсе (например, главное окно занимает весь экран) — точка с
    наименьшим перекрытием с ``blocked``.
    """
    point = random_free_point(free_bands(area, blocked), width, height)
    if point is not None:
        return point
    if blocked is not None and not blocked.isEmpty():
        return least_overlap_point(area, blocked, width, height)
    return area.left(), area.top()
