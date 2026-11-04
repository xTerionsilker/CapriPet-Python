from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QGuiApplication

from ..core.settings import set_config_value
from ..effects.lightning_tether import LightningTetherOverlay
from ..effects.transition import TransitionOverlay

if TYPE_CHECKING:
    from .pet_window import CapriWindow


class TeleportController:
    """Управляет прицеливанием молнией и эффектом телепортации окна."""

    def __init__(self, window: CapriWindow) -> None:
        self._window = window
        self._lightning_overlay: LightningTetherOverlay | None = None
        self._is_lightning_aiming: bool = False
        self._teleport_overlay_out: TransitionOverlay | None = None
        self._teleport_overlay_in: TransitionOverlay | None = None

    @property
    def is_aiming(self) -> bool:
        return self._is_lightning_aiming

    def _ensure_lightning_overlay(self) -> LightningTetherOverlay:
        if self._lightning_overlay is None:
            self._lightning_overlay = LightningTetherOverlay()
        return self._lightning_overlay

    def handle_mouse_press(self, event) -> bool:
        if event.button() == Qt.MouseButton.RightButton:
            if self._is_lightning_aiming:
                self.cancel_aiming()
            return False

        if event.button() == Qt.MouseButton.LeftButton:
            self._is_lightning_aiming = True
            self._window.surge_ticks = max(self._window.surge_ticks, 14)
            self._window.inactivity_manager.set_paused(True)
            self._window.update()

            cursor_pos = event.globalPosition().toPoint()
            pet_center = self._window.geometry().center()
            overlay = self._ensure_lightning_overlay()
            overlay.activate(pet_center, cursor_pos, self._window.geometry())
            return True

        return False

    def handle_mouse_move(self, event) -> bool:
        if self._is_lightning_aiming:
            cursor_pos = event.globalPosition().toPoint()
            pet_center = self._window.geometry().center()
            overlay = self._ensure_lightning_overlay()
            overlay.update_start(pet_center, self._window.geometry())
            overlay.update_target(cursor_pos)
            self._window.surge_ticks = max(self._window.surge_ticks, 6)
            self._window.inactivity_manager.reset_timer()
            self._window.update()
            return True
        return False

    def handle_mouse_release(self, event) -> bool:
        if event.button() == Qt.MouseButton.LeftButton and self._is_lightning_aiming:
            self._is_lightning_aiming = False
            self._window.inactivity_manager.set_paused(False)
            target_pos = event.globalPosition().toPoint()
            if self._lightning_overlay is not None:
                self._lightning_overlay.deactivate()

            self._window.surge_ticks = max(self._window.surge_ticks, 10)
            self._window.update()

            self.teleport_to_point(target_pos)
            return True
        return False

    def cancel_aiming(self) -> None:
        self._is_lightning_aiming = False
        self._window.inactivity_manager.set_paused(False)
        if self._lightning_overlay is not None:
            self._lightning_overlay.deactivate()
        self._window.update()

    def teleport_to_point(self, target_center_point: QPoint) -> None:
        """Телепортирует окно в указанную точку с эффектом красных молний."""
        w = self._window.width()
        h = self._window.height()
        target_top_left = QPoint(target_center_point.x() - w // 2, target_center_point.y() - h // 2)

        from_rect = QRect(self._window.geometry())
        to_rect = QRect(target_top_left.x(), target_top_left.y(), w, h)

        dx = abs(from_rect.center().x() - to_rect.center().x())
        dy = abs(from_rect.center().y() - to_rect.center().y())
        if dx < 12 and dy < 12:
            return

        target_screen = None
        for scr in QGuiApplication.screens():
            if scr.geometry().contains(target_center_point):
                target_screen = scr
                break
        if target_screen is None:
            target_screen = self._window.screen() or QGuiApplication.primaryScreen()

        screen_rect = target_screen.geometry() if target_screen is not None else to_rect

        if self._teleport_overlay_out is not None:
            try:
                self._teleport_overlay_out.close()
            except Exception:
                pass
            self._teleport_overlay_out = None
        if self._teleport_overlay_in is not None:
            try:
                self._teleport_overlay_in.close()
            except Exception:
                pass
            self._teleport_overlay_in = None

        def on_out_peak() -> None:
            self._window.hide()

        def on_out_finished() -> None:
            self._teleport_overlay_out = None
            if self._window.is_closing:
                return

            self._window.setGeometry(to_rect)
            wh = self._window.windowHandle()
            if wh is not None and target_screen is not None:
                wh.setScreen(target_screen)

            set_config_value("window.position", {"x": to_rect.x(), "y": to_rect.y()})
            set_config_value("window.overlay_position", {"x": to_rect.x(), "y": to_rect.y()})

            self._window.set_pose("idle")

            def on_in_peak() -> None:
                self._window.show()
                self._window.raise_()
                self._window.set_pose("idle")
                self._window.update()

            def on_in_finished() -> None:
                self._teleport_overlay_in = None
                self._window.show()
                self._window.raise_()
                self._window.surge_ticks = 8
                self._window.update()

            self._teleport_overlay_in = TransitionOverlay(
                screen_rect,
                to_rect,
                "in",
                target=self._window,
                on_peak=on_in_peak,
                target_point=from_rect.center(),
            )
            self._teleport_overlay_in.finished.connect(on_in_finished)
            self._teleport_overlay_in.start()

        self._window.set_pose("idle")
        self._teleport_overlay_out = TransitionOverlay(
            self._window.screen().geometry() if self._window.screen() else from_rect,
            from_rect,
            "out",
            target=self._window,
            on_peak=on_out_peak,
            target_point=to_rect.center(),
        )
        self._teleport_overlay_out.finished.connect(on_out_finished)
        self._teleport_overlay_out.start()
