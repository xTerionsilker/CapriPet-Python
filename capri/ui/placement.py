from __future__ import annotations

import random

from PySide6.QtCore import QRect

GAP = 24

OVERLAP_ATTEMPTS = 200


def free_bands(area: QRect, blocked: QRect | None) -> list[QRect]:
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
    point = random_free_point(free_bands(area, blocked), width, height)
    if point is not None:
        return point
    if blocked is not None and not blocked.isEmpty():
        return least_overlap_point(area, blocked, width, height)
    return area.left(), area.top()


def pick_side_position(
    area: QRect, target: QRect, width: int, height: int, gap: int = GAP
) -> tuple[int, int]:
    """Размещает окно строго справа или слева от целевого прямоугольника target."""
    # Возможные позиции по горизонтали
    right_x = target.right() + gap
    left_x = target.left() - gap - width

    # Проверяем, помещается ли справа и слева на экране
    fits_right = right_x + width <= area.right()
    fits_left = left_x >= area.left()

    # Выбираем сторону
    if fits_right and fits_left:
        # Если помещается с обеих сторон, выбираем случайную
        chosen_x = random.choice((right_x, left_x))
    elif fits_right:
        chosen_x = right_x
    elif fits_left:
        chosen_x = left_x
    else:
        # Если окно шире оставшегося пространства с обеих сторон,
        # выбираем ту сторону, где места объективно больше
        space_right = max(0, area.right() - target.right() - gap)
        space_left = max(0, target.left() - area.left() - gap)
        if space_right >= space_left:
            chosen_x = max(area.left(), min(right_x, area.right() - width))
        else:
            chosen_x = max(area.left(), min(left_x, area.right() - width))

    # Вертикальное выравнивание: центрируем относительно target с ограничением границ экрана
    ideal_y = target.center().y() - height // 2
    max_y = max(area.top(), area.bottom() - height)
    chosen_y = max(area.top(), min(ideal_y, max_y))

    return chosen_x, chosen_y

