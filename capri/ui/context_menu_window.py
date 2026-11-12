"""Центрированное 16:9 киберпанк-окно контекстного меню."""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer, Signal
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
    NEON_VIOLET,
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


class DatamoshOverlay(QWidget):
    """Кинетический оверлей эффекта Blackwall Datamosh при открытии/закрытии."""

    def __init__(self, parent: CyberContextMenuWindow) -> None:
        super().__init__(parent)
        self._hub = parent
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, event: Any) -> None:
        phase = self._hub.anim_phase
        if phase not in ("opening", "closing"):
            return

        prog = self._hub.anim_progress
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        intensity = (1.0 - prog) if phase == "opening" else prog
        frame_idx = int(prog * 15)
        rng = random.Random(frame_idx * 31 + (7 if phase == "opening" else 13))

        # 1. Горизонтальные датамош-блоки с хроматическим сдвигом
        for _ in range(rng.randint(4, 8)):
            sy = rng.randint(0, max(1, h - 25))
            sh = rng.randint(8, 28)
            ox = rng.choice([-1, 1]) * rng.randint(10, int(45 * intensity + 12))
            painter.fillRect(
                QRect(max(0, ox), sy, w, sh),
                QColor(2, 1, 6, int(160 * intensity)),
            )
            col_crimson = QColor(NEON_CRIMSON)
            col_crimson.setAlpha(int(220 * intensity))
            painter.fillRect(
                QRect(max(0, ox - 3), sy, rng.randint(2, 4), sh),
                col_crimson,
            )
            col_violet = QColor(NEON_VIOLET)
            col_violet.setAlpha(int(200 * intensity))
            painter.fillRect(
                QRect(min(w - 3, ox + w - 2), sy, rng.randint(2, 4), sh),
                col_violet,
            )

        # 2. Неоновые линии телеметрии
        for _ in range(rng.randint(3, 6)):
            ly = rng.randint(4, h - 4)
            lx = rng.randint(0, max(1, w - 120))
            lw = rng.randint(30, 160)
            col = rng.choice([QColor(6, 248, 104), QColor(18, 110, 233)])
            col.setAlpha(int(200 * intensity))
            painter.fillRect(QRect(lx, ly, lw, 2), col)

        # 3. Белая вспышка в ядре
        flash = max(0.0, 1.0 - prog * 2.5) if phase == "opening" else max(0.0, (prog - 0.6) * 2.5)
        if flash > 0.05:
            cy = h // 2 + rng.randint(-12, 12)
            painter.fillRect(QRect(0, cy, w, 2), QColor(249, 249, 249, int(255 * flash)))

        # 4. Сканирующие полосы CRT
        scan_a = int(35 * intensity)
        if scan_a > 0:
            painter.setPen(QPen(QColor(246, 2, 63, scan_a), 1))
            for y in range(0, h, 3):
                painter.drawLine(0, y, w, y)

        painter.end()


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

        self._anim_phase: str = "none"
        self._anim_progress: float = 0.0
        self._anim_duration: float = 0.16
        self._anim_start_time: float = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._on_anim_tick)

        self._init_geometry()
        self._init_ui()
        self._overlay = DatamoshOverlay(self)
        self._overlay.setGeometry(self.rect())

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

        lbl_title = QLabel("[ONLINE] CAPRI//NEURAL_LINK", self)
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
    @property
    def anim_phase(self) -> str:
        return self._anim_phase

    @property
    def anim_progress(self) -> float:
        return self._anim_progress

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_overlay") and self._overlay is not None:
            self._overlay.setGeometry(self.rect())
            self._overlay.raise_()

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        if hasattr(self, "_overlay") and self._overlay is not None:
            self._overlay.setGeometry(self.rect())
            self._overlay.raise_()
        self._start_open_animation()

    def close(self, immediate: bool = False) -> bool:
        if immediate or not self.isVisible() or self._anim_phase in ("closing", "closed"):
            self._anim_phase = "closed"
            self._anim_timer.stop()
            super().reject()
            return True
        self._start_close_animation()
        return False

    def reject(self) -> None:
        if self._anim_phase == "closed" or not self.isVisible():
            self._anim_timer.stop()
            super().reject()
            return
        if self._anim_phase != "closing":
            self._start_close_animation()

    def accept(self) -> None:
        if self._anim_phase == "closed" or not self.isVisible():
            self._anim_timer.stop()
            super().accept()
            return
        if self._anim_phase != "closing":
            self._start_close_animation()

    def closeEvent(self, event: Any) -> None:
        if self._anim_phase == "closed" or not self.isVisible():
            self._anim_timer.stop()
            super().reject()
            super().closeEvent(event)
            return

        if self._anim_phase == "closing":
            event.ignore()
            return

        event.ignore()
        self._start_close_animation()

    def _start_open_animation(self) -> None:
        self._anim_phase = "opening"
        self._anim_progress = 0.0
        self._anim_start_time = time.monotonic()
        self.setWindowOpacity(0.2)
        try:
            get_speech_sfx().play_swoosh()
        except Exception:
            pass
        self._anim_timer.start()

    def _start_close_animation(self) -> None:
        self._anim_phase = "closing"
        self._anim_progress = 0.0
        self._anim_start_time = time.monotonic()
        try:
            get_speech_sfx().play_close()
        except Exception:
            pass
        self._anim_timer.start()

    def _on_anim_tick(self) -> None:
        elapsed = time.monotonic() - self._anim_start_time
        prog = min(1.0, elapsed / self._anim_duration) if self._anim_duration > 0 else 1.0
        self._anim_progress = prog

        if self._anim_phase == "opening":
            self.setWindowOpacity(min(1.0, 0.2 + 0.8 * prog))
            self._overlay.update()
            if prog >= 1.0:
                self._anim_phase = "none"
                self._anim_timer.stop()
                self.setWindowOpacity(1.0)
                self._overlay.update()

        elif self._anim_phase == "closing":
            self.setWindowOpacity(max(0.0, 1.0 - prog))
            self._overlay.update()
            if prog >= 1.0:
                self._anim_phase = "closed"
                self._anim_timer.stop()
                super().reject()


__all__ = [
    "CyberTabBar",
    "CyberContextMenuWindow",
]
