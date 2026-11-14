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

# Цветовая палитра Capri (строго 6 цветов Studio Trigger)
COLOR_CRIMSON = QColor("#F6023F")
COLOR_ACID_GREEN = QColor("#06F868")
COLOR_VIOLET = QColor("#9E1FDE")
COLOR_OBSIDIAN = QColor("#020106")
COLOR_WHITE = QColor("#F9F9F9")
COLOR_ELECTRIC_BLUE = QColor("#126EE9")

PALETTE_TINT_COLORS: tuple[QColor, ...] = (
    COLOR_CRIMSON,
    COLOR_ACID_GREEN,
    COLOR_ELECTRIC_BLUE,
    COLOR_VIOLET,
    COLOR_WHITE,
)


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
        self._max_timeout_ms = max(4000, duration_ms)
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

        # Параметры колонок: (скорость, задержка старта, текущее смещение, цвет палитры)
        self._strip_speeds: list[float] = [random.uniform(260.0, 560.0) for _ in range(num_strips)]
        self._strip_delays: list[float] = [random.uniform(0.0, 0.22) for _ in range(num_strips)]
        self._strip_offsets: list[float] = [0.0] * num_strips
        self._strip_colors: list[QColor] = [random.choice(PALETTE_TINT_COLORS) for _ in range(num_strips)]

        # Таймер анимации
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(20)  # ~50 FPS
        self._anim_timer.timeout.connect(self._on_tick)

    @property
    def strip_colors(self) -> list[QColor]:
        """Список цветов палитры персонажа, назначенных столбцам."""
        return self._strip_colors

    @property
    def strip_offsets(self) -> list[float]:
        """Текущие вертикальные смещения столбцов."""
        return self._strip_offsets

    def start(self) -> None:
        """Запускает отображение оверлея и таймер анимации."""
        self._start_time = time.monotonic()
        self.show()
        self._anim_timer.start()

    def _on_tick(self) -> None:
        if self._start_time == 0.0:
            self._start_time = time.monotonic()
        elapsed = time.monotonic() - self._start_time
        elapsed_ms = elapsed * 1000.0

        # Обновление смещений полос
        for i in range(len(self._strip_offsets)):
            delay = self._strip_delays[i]
            if elapsed > delay:
                dt = elapsed - delay
                # Квадратичное ускорение гравитации стекания
                self._strip_offsets[i] = self._strip_speeds[i] * (dt**1.4)

        h = float(self.height())
        # Эффект завершается только когда все столбцы полностью стекли за нижний край
        all_descended = all(offset >= h for offset in self._strip_offsets)
        if all_descended or elapsed_ms >= self._max_timeout_ms:
            self._cleanup_and_finish()
            return

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

            # Случайный сдвиг по цвету (полупрозрачный тинт палитры персонажа)
            tint = QColor(self._strip_colors[i])
            tint.setAlpha(40)
            painter.fillRect(target_rect, tint)

            # Если полоса уже потекла, рисуем неоновый глитч-срез
            if dy > 0:
                # Верхняя полоса разрыва (Blackwall bleed) в цвет столбца
                painter.setPen(QPen(self._strip_colors[i], 1))
                painter.drawLine(x, dy, x + actual_w, dy)

                # Периодические микро-капли
                if i % 4 == 0:
                    dot_color = COLOR_WHITE if (i // 4) % 2 == 0 else COLOR_VIOLET
                    painter.setPen(QPen(dot_color, 2))
                    painter.drawPoint(QPoint(x + actual_w // 2, dy + 2))
