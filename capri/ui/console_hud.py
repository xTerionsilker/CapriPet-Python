"""Безрамочный Cyber HUD терминал прямого ввода команд в стилистике Cyberpunk.

Предоставляет компактную строку ввода команд (Quick Bar) рядом со спрайтом Капри
с историей команд, автодополнением и фирменной кнопкой завершения [TERMINATE].
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .speech_sfx import get_speech_sfx
from .theme import (
    ACID_GREEN,
    CSS_CYBER_TERMINAL,
    NEON_CRIMSON,
    OBSIDIAN_BLACK,
    PURE_WHITE,
    get_hud_font,
    get_terminal_font,
)

if TYPE_CHECKING:
    from .pet_window import CapriWindow

_CORNER_CUT = 10
_MARGIN_PET = 16


class CyberConsoleHud(QWidget):
    """Киберпанк Quick-Bar консоль прямого ввода команд."""

    def __init__(
        self,
        command_executor: Callable[[str], None],
        pet_window: CapriWindow | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self._command_executor = command_executor
        self._pet_window = pet_window

        self.setWindowTitle("Capri Cyberdeck Console")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self._history: list[str] = []
        self._history_index: int = -1
        self._temp_input: str = ""
        self._drag_start_pos: QPoint | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        self.setFixedSize(460, 84)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.setSpacing(6)

        # Верхняя панель заголовка
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Контейнер ввода и кнопки TERMINATE
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(8)

        self._input_line = QLineEdit(self)
        self._input_line.setPlaceholderText("SYS//ENTER_DIRECTIVE...")
        self._input_line.setFont(get_terminal_font(pixel_size=13))
        self._input_line.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: #06050C;
                color: {PURE_WHITE};
                border: 1px solid {ACID_GREEN};
                padding: 4px 8px;
                font-family: {CSS_CYBER_TERMINAL};
                selection-background-color: {NEON_CRIMSON};
                selection-color: {PURE_WHITE};
            }}
            QLineEdit:focus {{
                border: 1px solid {NEON_CRIMSON};
            }}
            """
        )
        self._input_line.returnPressed.connect(self._on_submit)
        self._input_line.installEventFilter(self)

        self._terminate_btn = QPushButton("TERMINATE", self)
        self._terminate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._terminate_btn.setFont(get_hud_font(pixel_size=11, bold=True))
        self._terminate_btn.setFixedHeight(28)
        self._terminate_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {OBSIDIAN_BLACK};
                color: {NEON_CRIMSON};
                border: 1px solid {NEON_CRIMSON};
                padding: 4px 10px;
                font-family: {CSS_CYBER_TERMINAL};
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {NEON_CRIMSON};
                color: {OBSIDIAN_BLACK};
            }}
            QPushButton:pressed {{
                background-color: #A00228;
                color: {PURE_WHITE};
            }}
            """
        )
        self._terminate_btn.clicked.connect(self.hide_console)

        input_row.addWidget(self._input_line, stretch=1)
        input_row.addWidget(self._terminate_btn, stretch=0)

        main_layout.addLayout(header_layout)
        main_layout.addLayout(input_row)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Начало перетаскивания окна консоли за фон."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Перемещение окна консоли при зажатой ЛКМ."""
        if self._drag_start_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Завершение перетаскивания окна консоли."""
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Перехват навигации по истории команд (Up/Down) и клавиши Esc."""
        if watched is self._input_line and event.type() == QEvent.Type.KeyPress:
            key_event: QKeyEvent = event  # type: ignore[assignment]
            if key_event.key() == Qt.Key.Key_Escape:
                self.hide_console()
                return True
            if key_event.key() == Qt.Key.Key_Up:
                self._navigate_history(-1)
                return True
            if key_event.key() == Qt.Key.Key_Down:
                self._navigate_history(1)
                return True
        return super().eventFilter(watched, event)

    def _navigate_history(self, delta: int) -> None:
        if not self._history:
            return
        if self._history_index == -1:
            self._temp_input = self._input_line.text()
            if delta < 0:
                self._history_index = len(self._history) - 1
        else:
            new_idx = self._history_index + delta
            if 0 <= new_idx < len(self._history):
                self._history_index = new_idx
            elif new_idx >= len(self._history):
                self._history_index = -1
                self._input_line.setText(self._temp_input)
                return

        if self._history_index != -1:
            self._input_line.setText(self._history[self._history_index])

    def _on_submit(self) -> None:
        cmd_text = self._input_line.text().strip()
        if not cmd_text:
            return

        if not self._history or self._history[-1] != cmd_text:
            self._history.append(cmd_text)
        self._history_index = -1
        self._temp_input = ""

        # Воспроизводим кибер-клик отправки
        get_speech_sfx().play_chirp()

        # Очищаем строку ввода для следующих команд
        self._input_line.clear()

        # Передаём в исполнитель команд оркестратора
        self._command_executor(cmd_text)

    def show_console(self) -> None:
        """Показывает консоль рядом с окном Капри и активирует фокус ввода."""
        self._position_near_pet()
        self.show()
        self.raise_()
        self.activateWindow()
        self._input_line.setFocus()
        get_speech_sfx().play_voice_start()

    def hide_console(self) -> None:
        """Закрывает окно консоли."""
        get_speech_sfx().play_close()
        self.hide()

    def _position_near_pet(self) -> None:
        """Позиционирует окно консоли рядом со спрайтом Капри."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()

        target_x = geo.center().x() - self.width() // 2
        target_y = geo.center().y() - self.height() // 2

        if self._pet_window is not None:
            pet_geo = self._pet_window.geometry()
            # Пытаемся разместить слева или справа от Капри
            space_left = pet_geo.left() - geo.left()
            space_right = geo.right() - pet_geo.right()

            if space_right >= self.width() + _MARGIN_PET:
                target_x = pet_geo.right() + _MARGIN_PET
                target_y = pet_geo.center().y() - self.height() // 2
            elif space_left >= self.width() + _MARGIN_PET:
                target_x = pet_geo.left() - self.width() - _MARGIN_PET
                target_y = pet_geo.center().y() - self.height() // 2
            else:
                # Если сбоку места нет, над или под спрайтом
                target_x = pet_geo.center().x() - self.width() // 2
                if pet_geo.top() - geo.top() >= self.height() + _MARGIN_PET:
                    target_y = pet_geo.top() - self.height() - _MARGIN_PET
                else:
                    target_y = pet_geo.bottom() + _MARGIN_PET

        # Клампим в границы экрана
        clamped_x = max(geo.left() + 10, min(target_x, geo.right() - self.width() - 10))
        clamped_y = max(geo.top() + 10, min(target_y, geo.bottom() - self.height() - 10))
        self.move(clamped_x, clamped_y)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Отрисовка 45-градусного chamfered кибер-бокса с границей и сканлайнами."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        cut = _CORNER_CUT

        # Контур со срезанным правым верхним и левым нижним углами
        path = QPainterPath()
        path.moveTo(cut, 0)
        path.lineTo(w - cut, 0)
        path.lineTo(w, cut)
        path.lineTo(w, h - cut)
        path.lineTo(w - cut, h)
        path.lineTo(cut, h)
        path.lineTo(0, h - cut)
        path.lineTo(0, cut)
        path.closeSubpath()

        # Фон — Obsidian Black
        painter.fillPath(path, QColor(OBSIDIAN_BLACK))

        # Сканлайны
        scan_pen = QPen(QColor(18, 110, 233, 18), 1)  # Electric Blue subtle
        painter.setPen(scan_pen)
        for y in range(4, h - 4, 3):
            painter.drawLine(6, y, w - 6, y)

        # Рамка — Neon Crimson с акцентами Acid Green
        border_pen = QPen(QColor(NEON_CRIMSON), 1.5)
        painter.setPen(border_pen)
        painter.drawPath(path)

        # Техническая метка вверху
        painter.setFont(get_hud_font(pixel_size=9, bold=True))
        painter.setPen(QColor(ACID_GREEN))
        painter.drawText(16, 18, "SYS//CYBERDECK_DIRECT_LINK // PROTOCOL_0x8F")

        # Микро-индикатор активности
        painter.setBrush(QColor(ACID_GREEN))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(w - 22, 10, 8, 8)
