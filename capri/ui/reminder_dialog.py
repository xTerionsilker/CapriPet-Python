"""Cyberpunk styled modal dialog for configuring Capri autonomy reminder interval ranges."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .theme import (
    ACID_GREEN,
    CSS_CYBER_TERMINAL,
    CSS_CYBER_UI,
    ELECTRIC_BLUE,
    NEON_CRIMSON,
    OBSIDIAN_BLACK,
    PURE_WHITE,
    get_hud_font,
)


class ReminderRangeDialog(QDialog):
    """Диалоговое окно настройки пользовательского диапазона интервалов напоминаний."""

    def __init__(
        self,
        init_min: int,
        init_max: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("CAPRI // REMINDER_CONFIG")
        self._drag_pos: QPoint | None = None
        self._chamfer = 14
        self._shadow_offset = 6

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 32, 18, 18)
        layout.setSpacing(14)

        header = QLabel("НАСТРОЙКА ЧАСТОТЫ РЕПЛИК (МИН)")
        header.setStyleSheet(
            f"color: {ACID_GREEN}; font-family: {CSS_CYBER_TERMINAL}; "
            "font-weight: bold; font-size: 11px; letter-spacing: 1px;"
        )
        layout.addWidget(header)

        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(12)

        lbl_from = QLabel("ОТ:")
        lbl_from.setStyleSheet(
            f"color: {PURE_WHITE}; font-family: {CSS_CYBER_TERMINAL}; font-size: 11px; font-weight: bold;"
        )
        self.spin_from = QSpinBox()
        self.spin_from.setRange(1, 1440)
        self.spin_from.setValue(init_min)
        self.spin_from.setSuffix(" МИН")

        lbl_to = QLabel("ДО:")
        lbl_to.setStyleSheet(
            f"color: {PURE_WHITE}; font-family: {CSS_CYBER_TERMINAL}; font-size: 11px; font-weight: bold;"
        )
        self.spin_to = QSpinBox()
        self.spin_to.setRange(1, 1440)
        self.spin_to.setValue(init_max)
        self.spin_to.setSuffix(" МИН")

        spin_style = f"""
        QSpinBox {{
            background-color: {OBSIDIAN_BLACK};
            border: 1px solid {NEON_CRIMSON};
            color: {PURE_WHITE};
            padding: 5px 8px;
            font-family: {CSS_CYBER_TERMINAL};
            font-size: 12px;
            font-weight: bold;
            selection-background-color: {NEON_CRIMSON};
        }}
        QSpinBox:focus {{
            border: 1px solid {ACID_GREEN};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            background-color: {OBSIDIAN_BLACK};
            border-left: 1px solid {NEON_CRIMSON};
            width: 16px;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: rgba(246, 2, 63, 0.35);
        }}
        """
        self.spin_from.setStyleSheet(spin_style)
        self.spin_to.setStyleSheet(spin_style)

        self.spin_from.valueChanged.connect(self._on_from_changed)
        self.spin_to.valueChanged.connect(self._on_to_changed)

        inputs_layout.addWidget(lbl_from)
        inputs_layout.addWidget(self.spin_from)
        inputs_layout.addWidget(lbl_to)
        inputs_layout.addWidget(self.spin_to)
        layout.addLayout(inputs_layout)

        btns_layout = QHBoxLayout()
        btns_layout.addStretch()

        btn_cancel = QPushButton("ОТМЕНА")
        btn_ok = QPushButton("ПРИМЕНИТЬ")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)

        btn_style = f"""
        QPushButton {{
            background-color: {OBSIDIAN_BLACK};
            border: 1px solid {NEON_CRIMSON};
            color: {PURE_WHITE};
            font-family: {CSS_CYBER_UI};
            font-size: 11px;
            padding: 6px 16px;
            font-weight: bold;
            letter-spacing: 1px;
        }}
        QPushButton:hover {{
            border-color: {ACID_GREEN};
            color: {ACID_GREEN};
            background-color: rgba(6, 248, 104, 0.1);
        }}
        QPushButton:pressed {{
            background-color: rgba(246, 2, 63, 0.35);
            border-color: {NEON_CRIMSON};
            color: {PURE_WHITE};
        }}
        """
        btn_cancel.setStyleSheet(btn_style)
        btn_ok.setStyleSheet(btn_style)

        btns_layout.addWidget(btn_cancel)
        btns_layout.addWidget(btn_ok)
        layout.addLayout(btns_layout)

    def _on_from_changed(self, val: int) -> None:
        if self.spin_to.value() < val:
            self.spin_to.setValue(val)

    def _on_to_changed(self, val: int) -> None:
        if self.spin_from.value() > val:
            self.spin_from.setValue(val)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._drag_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = self.width()
        h = self.height()
        c = self._chamfer
        so = self._shadow_offset

        bw = max(1, w - so)
        bh = max(1, h - so)

        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(bw - c, 0)
        path.lineTo(bw, c)
        path.lineTo(bw, bh)
        path.lineTo(c, bh)
        path.lineTo(0, bh - c)
        path.closeSubpath()

        shadow_path = path.translated(so, so)
        painter.fillPath(shadow_path, QColor(246, 2, 63, 85))

        painter.fillPath(path, QColor(2, 1, 6, 248))

        painter.save()
        painter.setClipPath(path)
        scanline_pen = QPen(QColor(246, 2, 63, 14), 1)
        painter.setPen(scanline_pen)
        for y in range(0, bh, 3):
            painter.drawLine(0, y, bw, y)
        painter.restore()

        crimson_pen = QPen(QColor(NEON_CRIMSON), 2)
        painter.strokePath(path, crimson_pen)

        accent_pen = QPen(QColor(ACID_GREEN), 2)
        painter.setPen(accent_pen)
        painter.drawLine(bw - c, 0, bw, c)
        painter.drawLine(c, bh, 0, bh - c)

        painter.drawLine(0, 0, 10, 0)
        painter.drawLine(0, 0, 0, 10)
        painter.drawLine(0, bh - 10, 0, bh)
        painter.drawLine(0, bh, 10, bh)
        painter.drawLine(bw - 10, bh, bw, bh)
        painter.drawLine(bw, bh - 10, bw, bh)

        badge_rect = QRect(14, 6, max(10, bw - c - 20), 16)
        painter.fillRect(QRect(12, 6, 175, 16), QColor(246, 2, 63, 40))
        painter.setPen(QColor(ACID_GREEN))
        painter.setFont(get_hud_font(10, bold=True))
        painter.drawText(
            badge_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "[CAPRI://AUTONOMY_RANGE]",
        )

        painter.fillRect(QRect(bw - 26, 7, 10, 2), QColor(ACID_GREEN))
        painter.fillRect(QRect(bw - 13, 7, 6, 2), QColor(ELECTRIC_BLUE))
