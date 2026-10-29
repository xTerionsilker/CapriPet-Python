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

_CORNER_CUT = 9


class CyberMenu(QMenu):
    """Меню в стиле Cyberpunk 2077: обсидиановая панель, неоновые рамки и сканлайны."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(CYBER_MENU_STYLE)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.fillRect(rect, QColor(OBSIDIAN_BLACK))

        # Сканлайны ЭЛТ-панели.
        painter.setPen(QPen(QColor(242, 13, 46, 22), 1))
        for y in range(rect.top() + 2, rect.bottom(), 3):
            painter.drawLine(rect.left() + 2, y, rect.right() - 2, y)

        # Цифровые помехи в правом верхнем углу.
        painter.fillRect(QRect(rect.right() - 26, rect.top() + 4, 15, 2), QColor(ACID_GREEN))
        painter.fillRect(QRect(rect.right() - 20, rect.top() + 7, 8, 2), QColor(ELECTRIC_BLUE))
        painter.fillRect(QRect(rect.right() - 31, rect.top() + 10, 12, 1), QColor(NEON_VIOLET))

        # Двойная неоновая рамка.
        painter.setPen(QPen(QColor(NEON_CRIMSON), 2))
        painter.drawRect(rect.adjusted(1, 1, -1, -1))
        painter.setPen(QPen(QColor(ACID_GREEN), 1))
        painter.drawLine(rect.left() + 5, rect.top() + 5, rect.left() + 5, rect.top() + 25)

        # Срезанный угол и короткие акцентные штрихи.
        cut = _CORNER_CUT
        painter.fillRect(
            QRect(rect.right() - cut + 1, rect.top(), cut, cut), QColor(OBSIDIAN_BLACK)
        )
        painter.setPen(QPen(QColor(NEON_CRIMSON), 2))
        painter.drawLine(
            rect.right() - cut, rect.top() + 1, rect.right() - 1, rect.top() + cut
        )
        painter.fillRect(
            QRect(rect.left() + 1, rect.bottom() - 6, 16, 2), QColor(PURE_WHITE)
        )
        painter.fillRect(
            QRect(rect.left() + 19, rect.bottom() - 6, 7, 2), QColor(NEON_VIOLET)
        )
        painter.end()

        super().paintEvent(event)
