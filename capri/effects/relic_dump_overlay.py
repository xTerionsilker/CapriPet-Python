"""Киберпанк-оверлей мини-терминала сбоя памяти биочипа Arasaka Relic (Option A).

Отображает моноширинный дамп регистров памяти и исключений десинхронизации энграммы
в дуотоне Studio Trigger со скошенными углами 45° и CRT-схлопыванием.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPaintEvent, QPen, QPolygon
from PySide6.QtWidgets import QWidget

COLOR_CRIMSON = QColor("#F6023F")
COLOR_OBSIDIAN = QColor("#020106")
COLOR_ACID_GREEN = QColor("#06F868")
COLOR_WHITE = QColor("#F9F9F9")
COLOR_VIOLET = QColor("#9E1FDE")

DUMP_LINES: tuple[str, ...] = (
    ">> [ARASAKA_RELIC_SEC_FAULT]",
    ">> MEM_PAGE: 0xDEADBEEF :: BUFFER_BLEED",
    ">> ENGRAM_SYNC_FAILURE: 4_MINDS_COLLISION",
    ">> SOULKILLER_V4_CORE: RESYNC HOST LINK [OK]",
)


class RelicDumpOverlay(QWidget):
    """Миниатюрный экранный терминал дампа памяти энграммы Relic."""

    finished = Signal()

    def __init__(
        self,
        target_rect: QRect,
        duration_ms: int = 2500,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._target_rect = target_rect
        self._duration_ms = duration_ms
        self._start_time: float = 0.0
        self._collapsing: bool = False
        self._collapse_progress: float = 0.0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.resize(340, 130)
        self._position_near_target()

        # Таймер тиков анимации и сканлайнов
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._on_tick)

    def _position_near_target(self) -> None:
        """Позиционирует оверлей рядом с целевым окном с контролем границ экрана."""
        screen = QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        # Пытаемся разместить справа от питомца
        x = self._target_rect.right() + 12
        y = self._target_rect.top()

        # Если выходит за правый край, размещаем слева
        if x + self.width() > screen_geo.right():
            x = self._target_rect.left() - self.width() - 12

        # Клампинг по границам экрана
        x = max(screen_geo.left() + 10, min(x, screen_geo.right() - self.width() - 10))
        y = max(screen_geo.top() + 10, min(y, screen_geo.bottom() - self.height() - 10))

        self.move(x, y)

    def get_dump_text(self) -> str:
        """Возвращает полный текст дампа памяти для проверок и логов."""
        return "\n".join(DUMP_LINES)

    def start(self) -> None:
        """Показывает оверлей и запускает таймер жизни."""
        self._start_time = time.monotonic()
        self.show()
        self._timer.start()

    def _on_tick(self) -> None:
        elapsed = (time.monotonic() - self._start_time) * 1000.0

        # Последние 200мс — схлопывание луча CRT
        collapse_window = 200.0
        if elapsed >= (self._duration_ms - collapse_window):
            self._collapsing = True
            rem = self._duration_ms - elapsed
            self._collapse_progress = max(0.0, min(1.0, 1.0 - (rem / collapse_window)))

        if elapsed >= self._duration_ms:
            self._timer.stop()
            self.finished.emit()
            self.close()
            return

        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        if self._collapsing:
            # CRT horizontal beam collapse
            painter.setPen(QPen(COLOR_WHITE, 2))
            center_y = h // 2
            beam_w = int(w * (1.0 - self._collapse_progress))
            start_x = (w - beam_w) // 2
            painter.drawLine(start_x, center_y, start_x + beam_w, center_y)
            return

        # Фон со скошенными 45° углами
        chamfer = 12
        poly = QPolygon(
            [
                QPoint(chamfer, 0),
                QPoint(w - 1, 0),
                QPoint(w - 1, h - chamfer),
                QPoint(w - chamfer, h - 1),
                QPoint(0, h - 1),
                QPoint(0, chamfer),
            ]
        )

        painter.setBrush(QColor(COLOR_OBSIDIAN.red(), COLOR_OBSIDIAN.green(), COLOR_OBSIDIAN.blue(), 230))
        painter.setPen(QPen(COLOR_CRIMSON, 1.5))
        painter.drawPolygon(poly)

        # Заголовок Arasaka BIOS
        header_rect = QRect(0, 0, w, 24)
        header_poly = QPolygon(
            [
                QPoint(chamfer, 0),
                QPoint(w - 1, 0),
                QPoint(w - 1, 24),
                QPoint(0, 24),
                QPoint(0, chamfer),
            ]
        )
        painter.setBrush(COLOR_CRIMSON)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(header_poly)

        font = QFont("JetBrains Mono", 8)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(COLOR_WHITE)
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignCenter, "// RELIC BIOCHIP EXCEPTION //")

        # Текст лога дампа памяти
        painter.setFont(QFont("JetBrains Mono", 7))
        text_y = 44
        line_height = 18

        for i, line in enumerate(DUMP_LINES):
            pen = COLOR_ACID_GREEN if i == 3 else (COLOR_CRIMSON if i == 0 else COLOR_WHITE)
            painter.setPen(pen)
            painter.drawText(16, text_y, line)
            text_y += line_height

        # Микро-глитч линия внизу
        painter.setPen(QPen(COLOR_VIOLET, 1))
        painter.drawLine(10, h - 4, w - 10, h - 4)
