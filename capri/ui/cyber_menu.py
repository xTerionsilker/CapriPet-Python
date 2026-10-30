from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QMenu, QWidget

from .theme import (
    ACID_GREEN,
    CYBER_MENU_STYLE,
    ELECTRIC_BLUE,
    NEON_CRIMSON,
    NEON_VIOLET,
    OBSIDIAN_BLACK,
    PURE_WHITE,
)

_CORNER_CUT = 10


class CyberMenu(QMenu):
    """Киберпанк меню в строгой эстетике Capri: угловатые вырезы, акценты HUD и микро-глитчи."""

    def __init__(self, parent: QWidget | None = None, title: str = "") -> None:
        super().__init__(title, parent)
        self.setStyleSheet(CYBER_MENU_STYLE)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        rect = self.rect().adjusted(0, 0, -1, -1)

        # 1. Тёмная глубинная подложка (Obsidian Black)
        painter.fillRect(rect, QColor(OBSIDIAN_BLACK))

        # 2. Тонкие сканлайны ЭЛТ дисплея
        scan_pen = QPen(QColor(242, 13, 46, 14), 1)
        painter.setPen(scan_pen)
        for y in range(rect.top() + 3, rect.bottom(), 3):
            painter.drawLine(rect.left() + 2, y, rect.right() - 2, y)

        # 3. Декоративные скошенные углы Cyberpunk HUD
        cut = _CORNER_CUT

        # Внешний контур с обрезанным верхним правым и нижним левым уголком
        border_pen = QPen(QColor(NEON_CRIMSON), 1)
        painter.setPen(border_pen)

        # Верхняя грань (заканчивается перед срезом справа)
        painter.drawLine(rect.left() + cut, rect.top(), rect.right() - cut, rect.top())
        # Срез правого верхнего угла
        painter.drawLine(rect.right() - cut, rect.top(), rect.right(), rect.top() + cut)
        # Правая грань
        painter.drawLine(rect.right(), rect.top() + cut, rect.right(), rect.bottom() - 3)
        # Нижняя грань (до среза слева)
        painter.drawLine(rect.right() - 3, rect.bottom(), rect.left() + cut, rect.bottom())
        # Срез левого нижнего угла
        painter.drawLine(rect.left() + cut, rect.bottom(), rect.left(), rect.bottom() - cut)
        # Левая грань
        painter.drawLine(rect.left(), rect.bottom() - cut, rect.left(), rect.top() + cut)
        # Срез левого верхнего угла
        painter.drawLine(rect.left(), rect.top() + cut, rect.left() + cut, rect.top())

        # 4. Технические угловые скобы и неоновые насечки (Acid Green & Crimson)
        # Скоба верх-лево (Acid Green)
        painter.setPen(QPen(QColor(ACID_GREEN), 2))
        painter.drawLine(rect.left() + 1, rect.top() + cut + 2, rect.left() + 1, rect.top() + cut + 16)
        painter.fillRect(QRect(rect.left() + 3, rect.top() + 3, 3, 3), QColor(ACID_GREEN))

        # Угловой индикатор статус-блока справа вверху
        painter.fillRect(QRect(rect.right() - 24, rect.top() + 3, 12, 2), QColor(ACID_GREEN))
        painter.fillRect(QRect(rect.right() - 10, rect.top() + 3, 6, 2), QColor(ELECTRIC_BLUE))

        # Скоба правый нижний угол (Electric Blue & Neon Crimson)
        painter.setPen(QPen(QColor(NEON_CRIMSON), 2))
        painter.drawLine(rect.right() - 1, rect.bottom() - 16, rect.right() - 1, rect.bottom() - 2)
        painter.drawLine(rect.right() - 16, rect.bottom() - 1, rect.right() - 2, rect.bottom() - 1)

        # Индикаторные маркеры снизу слева (White & Violet)
        painter.fillRect(QRect(rect.left() + cut + 2, rect.bottom() - 3, 10, 2), QColor(PURE_WHITE))
        painter.fillRect(QRect(rect.left() + cut + 14, rect.bottom() - 3, 6, 2), QColor(NEON_VIOLET))

        painter.end()

        # Стандартная отрисовка пунктов меню Qt
        super().paintEvent(event)
