"""Центрированное 16:9 киберпанк-окно контекстного меню."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QKeyEvent,
    QPainter,
    QPainterPath,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .context_menu_tabs import (
    AudioTabPage,
    CoreTabPage,
    SystemTabPage,
    VisualTabPage,
)
from .speech_sfx import get_speech_sfx
from .theme import (
    ACID_GREEN,
    CSS_CYBER_UI,
    ELECTRIC_BLUE,
    NEON_CRIMSON,
    OBSIDIAN_BLACK,
    PURE_WHITE,
)

if TYPE_CHECKING:
    pass

_HEADER_STYLE = f"""
QLabel {{
    color: {NEON_CRIMSON};
    font-family: {CSS_CYBER_UI};
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1.5px;
}}
"""
_CLOSE_BTN_STYLE = f"""
QPushButton {{
    background-color: transparent;
    color: {NEON_CRIMSON};
    border: 1px solid {NEON_CRIMSON};
    font-family: {CSS_CYBER_UI};
    font-size: 11px;
    font-weight: bold;
    padding: 2px 8px;
}}
QPushButton:hover {{
    background-color: {NEON_CRIMSON};
    color: {PURE_WHITE};
}}
"""

_TAB_BTN_DEFAULT = f"""
QPushButton {{
    background-color: {OBSIDIAN_BLACK};
    color: rgba(249, 249, 249, 0.7);
    border: 1px solid rgba(246, 2, 63, 0.4);
    border-bottom: 2px solid transparent;
    padding: 6px 16px;
    font-family: {CSS_CYBER_UI};
    font-size: 12px;
    font-weight: bold;
}}
QPushButton:hover {{
    color: {PURE_WHITE};
    border-color: {NEON_CRIMSON};
}}
"""

_TAB_BTN_ACTIVE = f"""
QPushButton {{
    background-color: rgba(246, 2, 63, 0.15);
    color: {ACID_GREEN};
    border: 1px solid {NEON_CRIMSON};
    border-bottom: 3px solid {ACID_GREEN};
    padding: 6px 16px;
    font-family: {CSS_CYBER_UI};
    font-size: 12px;
    font-weight: bold;
}}
"""
class CyberTabBar(QWidget):
    """Горизонтальная кибер-панель вкладок с поддержкой колесика мыши."""

    current_changed = Signal(int)

    def __init__(
        self, titles: list[str], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._titles = titles
        self._current_index = 0
        self._buttons: list[QPushButton] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for i, title in enumerate(self._titles):
            btn = QPushButton(f"[{title}]", self)
            btn.setStyleSheet(
                _TAB_BTN_ACTIVE if i == self._current_index else _TAB_BTN_DEFAULT
            )
            btn.clicked.connect(lambda _, idx=i: self.set_current_index(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)
        layout.addStretch()

    def current_index(self) -> int:
        return self._current_index

    def set_current_index(self, index: int) -> None:
        if not (0 <= index < len(self._titles)):
            return
        if self._current_index == index:
            return
        self._current_index = index
        for i, btn in enumerate(self._buttons):
            btn.setStyleSheet(
                _TAB_BTN_ACTIVE if i == index else _TAB_BTN_DEFAULT
            )
        try:
            get_speech_sfx().play_relay_snap()
        except Exception:
            pass
        self.current_changed.emit(index)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta < 0:
            next_idx = (self._current_index + 1) % len(self._titles)
            self.set_current_index(next_idx)
        elif delta > 0:
            next_idx = (self._current_index - 1) % len(self._titles)
            self.set_current_index(next_idx)
        event.accept()


class CyberContextMenuWindow(QDialog):
    """16:9 центрированное киберпанк-окно управления питомцем."""

    DEFAULT_WIDTH = 800
    DEFAULT_HEIGHT = 450

    def __init__(self, window: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pet_window = window

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._init_geometry()
        self._init_ui()

    def _init_geometry(self) -> None:
        screen = QGuiApplication.primaryScreen()
        for s in QGuiApplication.screens():
            if s.geometry().contains(QPoint(100, 100)):
                screen = s
                break

        w = self.DEFAULT_WIDTH
        h = self.DEFAULT_HEIGHT

        if screen:
            avail = screen.availableGeometry()
            # If screen is too small, scale down keeping 16:9
            max_w = int(avail.width() * 0.85)
            max_h = int(avail.height() * 0.85)
            if w > max_w or h > max_h:
                scale = min(max_w / w, max_h / h)
                w = int(w * scale)
                h = int(w * (9 / 16))

            x = avail.left() + (avail.width() - w) // 2
            y = avail.top() + (avail.height() - h) // 2
            self.setGeometry(x, y, w, h)
        else:
            self.resize(w, h)
    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel("CAPRI//CONTROL_HUB [REV.46]", self)
        lbl_title.setStyleSheet(_HEADER_STYLE)
        header_layout.addWidget(lbl_title)

        header_layout.addStretch()

        btn_close = QPushButton("[X]", self)
        btn_close.setStyleSheet(_CLOSE_BTN_STYLE)
        btn_close.clicked.connect(self.close)
        header_layout.addWidget(btn_close)
        main_layout.addLayout(header_layout)

        # Tab bar
        tab_titles = ["CORE", "AUDIO", "VISUAL", "SYSTEM"]
        self.tab_bar = CyberTabBar(tab_titles, self)
        self.tab_bar.current_changed.connect(self._on_tab_changed)
        main_layout.addWidget(self.tab_bar)

        # Stacked pages
        self.stack = QStackedWidget(self)
        self.page_core = CoreTabPage(self.pet_window, self)
        self.page_audio = AudioTabPage(self.pet_window, self)
        self.page_visual = VisualTabPage(self.pet_window, self)
        self.page_system = SystemTabPage(self.pet_window, self)

        self.stack.addWidget(self.page_core)
        self.stack.addWidget(self.page_audio)
        self.stack.addWidget(self.page_visual)
        self.stack.addWidget(self.page_system)

        main_layout.addWidget(self.stack, 1)

    def _on_tab_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        rect = self.rect().adjusted(0, 0, -1, -1)
        w = rect.width()
        h = rect.height()
        c = 16

        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(w - c, 0)
        path.lineTo(w, c)
        path.lineTo(w, h)
        path.lineTo(c, h)
        path.lineTo(0, h - c)
        path.closeSubpath()

        painter.fillPath(path, QColor(OBSIDIAN_BLACK))

        painter.save()
        painter.setClipPath(path)
        scan_pen = QPen(QColor(246, 2, 63, 14), 1)
        painter.setPen(scan_pen)
        for y in range(rect.top() + 3, rect.bottom(), 3):
            painter.drawLine(rect.left(), y, rect.right(), y)
        painter.restore()

        crimson_pen = QPen(QColor(NEON_CRIMSON), 1)
        painter.strokePath(path, crimson_pen)

        accent_pen = QPen(QColor(ACID_GREEN), 2)
        painter.setPen(accent_pen)
        painter.drawLine(w - c, 0, w, c)
        painter.drawLine(c, h, 0, h - c)

        painter.fillRect(QRect(w - 28, 4, 12, 2), QColor(ACID_GREEN))
        painter.fillRect(QRect(w - 14, 4, 8, 2), QColor(ELECTRIC_BLUE))
        painter.fillRect(QRect(4, h - 6, 10, 2), QColor(PURE_WHITE))
        painter.end()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow():
            self.close()
        super().changeEvent(event)
    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        try:
            get_speech_sfx().play_swoosh()
        except Exception:
            pass

    def closeEvent(self, event: Any) -> None:
        try:
            get_speech_sfx().play_close()
        except Exception:
            pass
        super().closeEvent(event)


__all__ = [
    "CyberTabBar",
    "CyberContextMenuWindow",
]
