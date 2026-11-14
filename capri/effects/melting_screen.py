"""Процедурный полноэкранный вирусный оверлей «Тающий экран» (Melting Screen Glitch).

Имитирует аналоговое стекание строк/колонок кадра при перегрузке биочипа
в дуотоне Studio Trigger (#F6023F Crimson, #06F868 Acid Green) без перехвата пользовательского ввода.
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from PySide6.QtGui import QScreen

# Цветовая палитра Capri
COLOR_CRIMSON = QColor("#F6023F")
COLOR_ACID_GREEN = QColor("#06F868")
COLOR_VIOLET = QColor("#9E1FDE")
COLOR_OBSIDIAN = QColor("#020106")


class MeltingScreenOverlay(QWidget):
    """Полноэкранный прозрачный для мыши оверлей визуального таяния экрана."""

    finished = Signal()

    def __init__(
        self,
        screen: QScreen | None = None,
        duration_ms: int = 1400,
        strip_width: int = 6,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._duration_ms = duration_ms
        self._strip_width = max(2, strip_width)
        self._start_time: float = 0.0

        # Конфигурация окна: без рамок, поверх всех окон, прозрачно для ввода мыши и клавиатуры
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self._target_screen = screen or QGuiApplication.primaryScreen()
        if self._target_screen is not None:
            geo = self._target_screen.geometry()
            self.setGeometry(geo)
            try:
                self._pixmap = self._target_screen.grabWindow(0)
            except Exception:
                self._pixmap = QPixmap(geo.size())
                self._pixmap.fill(Qt.GlobalColor.black)
        else:
            self.setGeometry(0, 0, 800, 600)
            self._pixmap = QPixmap(800, 600)
            self._pixmap.fill(Qt.GlobalColor.black)

        # Вычисление колонок для эффекта стекания
        width = self.width()
        num_strips = max(1, (width + self._strip_width - 1) // self._strip_width)

        # Параметры колонок: (скорость, задержка старта, текущее смещение)
        self._strip_speeds: list[float] = [random.uniform(180.0, 480.0) for _ in range(num_strips)]
        self._strip_delays: list[float] = [random.uniform(0.0, 0.25) for _ in range(num_strips)]
        self._strip_offsets: list[float] = [0.0] * num_strips

        # Таймер анимации
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(20)  # ~50 FPS
        self._anim_timer.timeout.connect(self._on_tick)

    def start(self) -> None:
        """Запускает отображение оверлея и таймер анимации."""
        self._start_time = time.monotonic()
        self.show()
        self._anim_timer.start()

    def _on_tick(self) -> None:
        elapsed = time.monotonic() - self._start_time
        elapsed_ms = elapsed * 1000.0

        if elapsed_ms >= self._duration_ms:
            self._cleanup_and_finish()
            return

        # Обновление смещений полос
        for i in range(len(self._strip_offsets)):
            delay = self._strip_delays[i]
            if elapsed > delay:
                dt = elapsed - delay
                # Квадратичное ускорение гравитации стекания
                self._strip_offsets[i] = self._strip_speeds[i] * (dt**1.4)

        self.update()

    def _cleanup_and_finish(self) -> None:
        self._anim_timer.stop()
        self.finished.emit()
        self.close()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        if self._pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), COLOR_OBSIDIAN)

        w = self.width()
        h = self.height()
        strip_w = self._strip_width

        crimson_pen = QPen(COLOR_CRIMSON, 1)
        green_pen = QPen(COLOR_ACID_GREEN, 1)

        for i, offset in enumerate(self._strip_offsets):
            x = i * strip_w
            if x >= w:
                break
            actual_w = min(strip_w, w - x)
            dy = int(offset)

            # Отрисовка смещённой вертикальной полосы
            src_rect = QRect(x, 0, actual_w, h)
            target_rect = QRect(x, dy, actual_w, h)
            painter.drawPixmap(target_rect, self._pixmap, src_rect)

            # Если полоса уже потекла, рисуем неоновый глитч-срез
            if dy > 0:
                # Верхняя полоса разрыва (Blackwall bleed)
                painter.setPen(crimson_pen if i % 2 == 0 else green_pen)
                painter.drawLine(x, dy, x + actual_w, dy)

                # Периодические микро-капли
                if i % 5 == 0:
                    painter.setPen(QPen(COLOR_VIOLET, 2))
                    painter.drawPoint(QPoint(x + actual_w // 2, dy + 2))
