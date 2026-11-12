"""System tray integration and notification area management for CapriPet."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

CAPRI_ICON = (
    Path(__file__).resolve().parent.parent.parent
    / "assets"
    / "capri_icon.png"
)

if TYPE_CHECKING:
    from .pet_window import CapriWindow


class TrayManager:
    """Менеджер интеграции с системным треем операционной системы."""

    def __init__(
        self,
        window: CapriWindow | Any,
        tray_menu: QMenu | None = None,
    ) -> None:
        self._window = window
        self._tray_icon: QSystemTrayIcon | None = None
        self._tray_menu = tray_menu
        self.init_tray()

    @property
    def tray_icon(self) -> QSystemTrayIcon | None:
        return self._tray_icon

    def init_tray(self) -> None:
        icon = QIcon(str(CAPRI_ICON))
        if icon.isNull():
            pix = (
                self._window.pixmap
                if hasattr(self._window, "pixmap")
                and not self._window.pixmap.isNull()
                else QPixmap(32, 32)
            )
            icon = QIcon(pix)

        self._window.setWindowIcon(icon)
        app = QApplication.instance()
        if isinstance(app, (QApplication, QGuiApplication)):
            app.setWindowIcon(icon)

        from PySide6.QtCore import QObject

        parent_obj = self._window if isinstance(self._window, QObject) else None
        self._tray_icon = QSystemTrayIcon(icon, parent_obj)
        self._tray_icon.setToolTip("CapriPet")

        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _open_hub(self) -> None:
        from .context_menu_window import CyberContextMenuWindow

        win = getattr(self._window, "_context_menu_dialog", None)
        if (
            not isinstance(win, CyberContextMenuWindow)
            or not win.isVisible()
        ):
            win = CyberContextMenuWindow(self._window)
            self._window._context_menu_dialog = win
            win.exec()

    def _on_tray_activated(
        self, reason: QSystemTrayIcon.ActivationReason
    ) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._window.activate_command_mode()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            self._open_hub()
