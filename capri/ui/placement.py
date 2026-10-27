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


def pick_adjacent_position(
    area: QRect,
    target: QRect,
    width: int,
    height: int,
    gap: int = GAP,
    preferred_side: str | None = None,
    margin: int = 12,
) -> tuple[int, int, str]:
    """Размещает окно строго рядом с целевым прямоугольником target (Капри).

    Возвращает (x, y, side), где side: 'right' | 'left' | 'top' | 'bottom'.
    Порядок приоритетов:
    1. preferred_side (если передана и помещается без пересечения с target)
    2. Боковая сторона с наибольшим свободным пространством (справа или слева)
    3. Противоположная боковая сторона
    4. Сверху (top) над target
    5. Снизу (bottom) под target
    6. Позиция с наименьшим пересечением, если экран слишком мал.
    """
    safe_left = area.left() + margin
    safe_right = area.right() - margin
    safe_top = area.top() + margin
    safe_bottom = area.bottom() - margin

    # 1. Справа
    rx = target.right() + gap
    ry = target.center().y() - height // 2
    ry_clamped = max(safe_top, min(ry, safe_bottom - height))
    right_rect = QRect(rx, ry_clamped, width, height)
    fits_right = (rx + width <= safe_right) and not right_rect.intersects(target)

    # 2. Слева
    lx = target.left() - gap - width
    ly = target.center().y() - height // 2
    ly_clamped = max(safe_top, min(ly, safe_bottom - height))
    left_rect = QRect(lx, ly_clamped, width, height)
    fits_left = (lx >= safe_left) and not left_rect.intersects(target)

    # 3. Сверху
    tx = target.center().x() - width // 2
    tx_clamped = max(safe_left, min(tx, safe_right - width))
    ty = target.top() - gap - height
    top_rect = QRect(tx_clamped, ty, width, height)
    fits_top = (ty >= safe_top) and not top_rect.intersects(target)

    # 4. Снизу
    bx = target.center().x() - width // 2
    bx_clamped = max(safe_left, min(bx, safe_right - width))
    by = target.bottom() + gap
    bottom_rect = QRect(bx_clamped, by, width, height)
    fits_bottom = (by + height <= safe_bottom) and not bottom_rect.intersects(target)

    candidates: dict[str, tuple[int, int, bool, QRect]] = {
        "right": (rx, ry_clamped, fits_right, right_rect),
        "left": (lx, ly_clamped, fits_left, left_rect),
        "top": (tx_clamped, ty, fits_top, top_rect),
        "bottom": (bx_clamped, by, fits_bottom, bottom_rect),
    }

    # Если preferred_side задана и помещается без перекрытия
    if preferred_side and preferred_side in candidates and candidates[preferred_side][2]:
        x, y, _, _ = candidates[preferred_side]
        return x, y, preferred_side

    # Проверяем, с какой стороны от target больше места
    space_right = max(0, safe_right - target.right() - gap)
    space_left = max(0, target.left() - safe_left - gap)

    if space_right >= space_left:
        ordered_sides = ["right", "left", "top", "bottom"]
    else:
        ordered_sides = ["left", "right", "top", "bottom"]

    # Ищем первую сторону, которая помещается полностью
    for side in ordered_sides:
        x, y, fits, _ = candidates[side]
        if fits:
            return x, y, side

    # Если ни одна сторона не поместилась идеально (узкий экран/большое окно):
    # выбираем позицию с минимальным перекрытием с target
    best_side = ordered_sides[0]
    best_overlap = float("inf")
    best_x, best_y = candidates[best_side][0], candidates[best_side][1]

    for side in ("right", "left", "top", "bottom"):
        cand_x, cand_y, _, _ = candidates[side]
        clamped_x = max(safe_left, min(cand_x, safe_right - width))
        clamped_y = max(safe_top, min(cand_y, safe_bottom - height))
        clamped_rect = QRect(clamped_x, clamped_y, width, height)
        overlap = clamped_rect.intersected(target)
        overlap_area = overlap.width() * overlap.height() if not overlap.isEmpty() else 0
        if overlap_area < best_overlap:
            best_overlap = overlap_area
            best_side = side
            best_x, best_y = clamped_x, clamped_y

    return best_x, best_y, best_side


def pick_side_position(
    area: QRect, target: QRect, width: int, height: int, gap: int = GAP
) -> tuple[int, int]:
    """Размещает окно строго рядом с целевым прямоугольником target."""
    x, y, _ = pick_adjacent_position(area, target, width, height, gap=gap)
    return x, y

