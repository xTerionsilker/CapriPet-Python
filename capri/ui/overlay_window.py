from __future__ import annotations

import random
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QWidget


class CapriOverlayWindow(QWidget):
    """Плавающее поверх всех окон изображение питомца с глитч-эффектами."""

    def __init__(
        self,
        image_path: Path,
        on_interact: Callable[[], None] | None = None,
        on_context_menu: Callable[[QPoint], None] | None = None,
        on_moved: Callable[[QPoint], None] | None = None,
    ) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self._on_interact = on_interact
        self._on_context_menu = on_context_menu
        self._on_moved = on_moved
        self.setWindowTitle("Капри")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoFillBackground(False)

        self._pixmaps: dict[str, QPixmap] = {}
        self._load_pixmap("default", image_path)
        self._current_pose = "default"
        self._pixmap = self._pixmaps["default"]
        self.setFixedSize(self._pixmap.size())

        self._drag_offset: QPoint | None = None

        # Таймер для постоянной анимации небольших пиксельных глитчей
        self._glitch_timer = QTimer(self)
        self._glitch_timer.setInterval(80)
        self._glitch_timer.timeout.connect(self._on_glitch_tick)

    def _load_pixmap(self, name: str, path: Path) -> QPixmap:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            pixmap = QPixmap(420, 420)
        target_width = max(1, int(pixmap.width() / 1.5))
        target_height = max(1, int(pixmap.height() / 1.5))
        scaled = pixmap.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._pixmaps[name] = scaled
        return scaled

    def set_pose_image(self, pose_name: str, path: Path) -> None:
        """Переключает спрайт позы по пути к изображению."""
        if pose_name not in self._pixmaps:
            self._load_pixmap(pose_name, path)
        self._current_pose = pose_name
        self._pixmap = self._pixmaps[pose_name]
        self.update()


    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        self._glitch_timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._glitch_timer.stop()
        super().hideEvent(event)

    def _on_glitch_tick(self) -> None:
        # Случайный интервал для органичного мерцания глитчей
        self._glitch_timer.setInterval(random.randint(60, 110))
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        w = self._pixmap.width()
        h = self._pixmap.height()
        if w <= 0 or h <= 0:
            painter.end()
            return

        # Шанс активного импульса в текущем кадре
        active_glitch = random.random() < 0.55

        # 1. Отрисовка базового спрайта облика (с крупными сдвигами полос)
        if active_glitch and random.random() < 0.50:
            sy = (random.randint(0, max(0, h - 16)) // 4) * 4
            sh = random.choice((6, 8, 12, 16))
            dx = random.choice((-16, -12, -8, 8, 12, 16))
            if sy > 0:
                painter.drawPixmap(0, 0, self._pixmap, 0, 0, w, sy)
            painter.drawPixmap(dx, sy, self._pixmap, 0, sy, w, sh)
            bottom_y = sy + sh
            if bottom_y < h:
                painter.drawPixmap(
                    0, bottom_y, self._pixmap, 0, bottom_y, w, h - bottom_y
                )
        else:
            painter.drawPixmap(0, 0, self._pixmap)

        # 2. Наложение крупных глитчей красного и чёрного цвета
        # Применяем CompositionMode_SourceAtop, чтобы глитчи рисовались по силуэту облика
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceAtop
        )

        red_colors = (
            QColor(255, 0, 45, random.randint(200, 255)),
            QColor(255, 30, 75, random.randint(180, 245)),
            QColor(215, 0, 30, random.randint(210, 255)),
            QColor(255, 50, 90, random.randint(190, 240)),
        )
        black_colors = (
            QColor(0, 0, 0, random.randint(200, 255)),
            QColor(8, 8, 12, random.randint(190, 250)),
            QColor(16, 0, 8, random.randint(180, 240)),
        )
        glitch_colors = red_colors + black_colors

        # а) Крупные горизонтальные глитч-полосы
        bar_count = (
            random.randint(2, 5)
            if active_glitch
            else (random.randint(1, 2) if random.random() < 0.5 else 0)
        )
        for _ in range(bar_count):
            by = (random.randint(0, max(0, h - 8)) // 4) * 4
            bh = random.choice((4, 6, 8, 12))
            bw = (random.randint(w // 4, w) // 4) * 4
            bx = (random.randint(0, max(0, w - bw)) // 4) * 4
            color = random.choice(glitch_colors)
            painter.fillRect(bx, by, bw, bh, color)

        # б) Крупные пиксельные блоки (8x8, 12x8, 16x8, 20x12, 28x12 px)
        block_count = (
            random.randint(4, 9) if active_glitch else random.randint(1, 4)
        )
        for _ in range(block_count):
            bw = random.choice((8, 12, 16, 20, 28))
            bh = random.choice((6, 8, 12, 16))
            bx = (random.randint(0, max(0, w - bw)) // 4) * 4
            by = (random.randint(0, max(0, h - bh)) // 4) * 4
            color = random.choice(glitch_colors)
            painter.fillRect(bx, by, bw, bh, color)

        # в) Пиксельные шумовые квадраты красного и черного цвета (4x4 px)
        noise_count = (
            random.randint(6, 16) if active_glitch else random.randint(2, 6)
        )
        for _ in range(noise_count):
            nx = (random.randint(0, max(0, w - 4)) // 4) * 4
            ny = (random.randint(0, max(0, h - 4)) // 4) * 4
            color = random.choice(glitch_colors)
            painter.fillRect(nx, ny, 4, 4, color)

        # 3. Выступающие за силуэт красные и черные пиксельные блоки
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )
        if active_glitch and random.random() < 0.65:
            for _ in range(random.randint(2, 4)):
                ex = (random.randint(0, max(0, w - 8)) // 4) * 4
                ey = (random.randint(0, max(0, h - 8)) // 4) * 4
                ew = random.choice((4, 8))
                eh = random.choice((4, 6))
                spark_color = random.choice(glitch_colors)
                painter.fillRect(ex, ey, ew, eh, spark_color)

        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if callable(self._on_interact):
            self._on_interact()
        if event.button() == Qt.MouseButton.RightButton:
            if callable(self._on_context_menu):
                self._on_context_menu(event.globalPosition().toPoint())
                event.accept()
                return
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.windowHandle()
            if handle is not None and hasattr(handle, "startSystemMove"):
                handle.startSystemMove()
                event.accept()
                return
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._drag_offset is not None and self._on_moved is not None:
            self._on_moved(self.pos())
        self._drag_offset = None
        super().mouseReleaseEvent(event)
