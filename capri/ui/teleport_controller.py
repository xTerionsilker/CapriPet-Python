"""Контроллер телепортации и визуальных эффектов перемещения питомца.

Управляет эффектами молниевой привязки к курсору, направлением взгляда
и квантовой дезинтеграцией/материализацией окна питомца.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QGuiApplication

from ..core.settings import set_config_value
from ..effects.cursor_pointer import CursorPointerOverlay
from ..effects.lightning_tether import LightningTetherOverlay
from ..effects.transition import TransitionOverlay
from ..integrations.system_control import get_mouse_position, move_mouse_to

if TYPE_CHECKING:
    from .pet_window import CapriWindow


class TeleportController:
    """Контроллер квантовой телепортации и эффектов привязки к курсору."""

    def __init__(self, window: CapriWindow) -> None:
        self._window = window
        self._lightning_overlay: LightningTetherOverlay | None = None
        self._pointer_overlay: CursorPointerOverlay | None = None
        self._is_lightning_aiming: bool = False
        self._teleport_overlay_out: TransitionOverlay | None = None
        self._teleport_overlay_in: TransitionOverlay | None = None

        self._tracking_timer: QTimer = QTimer()
        self._tracking_timer.setInterval(16)
        self._tracking_timer.timeout.connect(self._on_tracking_tick)
        self._pull_start_time: float = 0.0
        self._pull_duration: float = 3.0
        self._pull_initial_cursor: QPoint = QPoint(0, 0)

    @property
    def is_aiming(self) -> bool:
        return self._is_lightning_aiming

    @property
    def is_tracking(self) -> bool:
        return self._tracking_timer.isActive()

    def _ensure_lightning_overlay(self) -> LightningTetherOverlay:
        if self._lightning_overlay is None:
            self._lightning_overlay = LightningTetherOverlay()
        return self._lightning_overlay

    def _ensure_pointer_overlay(self) -> CursorPointerOverlay:
        if self._pointer_overlay is None:
            self._pointer_overlay = CursorPointerOverlay()
        return self._pointer_overlay

    def point_at_mouse(self, pull_duration_seconds: float = 3.0) -> None:
        if self._is_lightning_aiming:
            self.cancel_aiming()

        cursor_pos = get_mouse_position()
        pet_center = self._window.geometry().center()
        overlay = self._ensure_pointer_overlay()
        overlay.activate(pet_center, cursor_pos)

        self._window.surge_ticks = max(self._window.surge_ticks, 10)
        self._window.inactivity_manager.set_paused(True)
        self._window.inactivity_manager.reset_timer()
        self._window.update()

        self._pull_start_time = time.monotonic()
        self._pull_duration = max(3.0, float(pull_duration_seconds))
        self._pull_initial_cursor = cursor_pos
        self._tracking_timer.start()

    def stop_pointing_at_mouse(self) -> None:
        if self._tracking_timer.isActive():
            self._tracking_timer.stop()
        if self._pointer_overlay is not None:
            self._pointer_overlay.start_fade_out()
        if not self._is_lightning_aiming:
            self._window.inactivity_manager.set_paused(False)
            self._window.inactivity_manager.reset_timer()
            self._window.update()

    def _on_tracking_tick(self) -> None:
        if self._window.is_closing:
            self.stop_pointing_at_mouse()
            return

        now = time.monotonic()
        elapsed = now - self._pull_start_time
        progress = max(0.0, min(1.0, elapsed / self._pull_duration))

        pet_center = self._window.geometry().center()
        get_mouse_position()

        t = progress * progress * (3.0 - 2.0 * progress)
        target_x = round(
            self._pull_initial_cursor.x()
            + (pet_center.x() - self._pull_initial_cursor.x()) * t
        )
        target_y = round(
            self._pull_initial_cursor.y()
            + (pet_center.y() - self._pull_initial_cursor.y()) * t
        )

        move_mouse_to(target_x, target_y)
        new_cursor = get_mouse_position()

        overlay = self._ensure_pointer_overlay()
        overlay.update_positions(pet_center, new_cursor)
        self._window.surge_ticks = max(self._window.surge_ticks, 4)
        self._window.update()

        distance_to_pet = (
            (new_cursor.x() - pet_center.x()) ** 2
            + (new_cursor.y() - pet_center.y()) ** 2
        ) ** 0.5
        if progress >= 1.0 or distance_to_pet <= 16:
            self.stop_pointing_at_mouse()

    def handle_mouse_press(self, event) -> bool:
        if event.button() == Qt.MouseButton.RightButton:
            if self._is_lightning_aiming:
                self.cancel_aiming()
            return False

        if event.button() == Qt.MouseButton.LeftButton:
            self._is_lightning_aiming = True
            self._window._is_dragging = True
            self._window.surge_ticks = max(self._window.surge_ticks, 14)
            self._window.inactivity_manager.set_paused(True)
            self._window.update()

            cursor_pos = event.globalPosition().toPoint()
            pet_center = self._window.geometry().center()
            overlay = self._ensure_lightning_overlay()
            overlay.activate(
                pet_center, cursor_pos, self._window.geometry()
            )
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
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._is_lightning_aiming
        ):
            self._is_lightning_aiming = False
            self._window._is_dragging = False
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
        self.stop_pointing_at_mouse()
        self._is_lightning_aiming = False
        self._window._is_dragging = False
        self._window.inactivity_manager.set_paused(False)
        if self._lightning_overlay is not None:
            self._lightning_overlay.deactivate()
        self._window.update()

    def teleport_to_point(
        self,
        target_center_point: QPoint,
        mode: str = "in",
        on_finished_callback: Callable[[], None] | None = None,
    ) -> None:

        w = self._window.width()
        h = self._window.height()
        target_top_left = QPoint(
            target_center_point.x() - w // 2,
            target_center_point.y() - h // 2,
        )

        from_rect = QRect(self._window.geometry())
        to_rect = QRect(target_top_left.x(), target_top_left.y(), w, h)

        dx = abs(from_rect.center().x() - to_rect.center().x())
        dy = abs(from_rect.center().y() - to_rect.center().y())
        if dx < 12 and dy < 12 and mode != "erratic_in":
            if on_finished_callback is not None:
                on_finished_callback()
            return

        target_screen = None
        for scr in QGuiApplication.screens():
            if scr.geometry().contains(target_center_point):
                target_screen = scr
                break
        if target_screen is None:
            target_screen = (
                self._window.screen() or QGuiApplication.primaryScreen()
            )

        screen_rect = (
            target_screen.geometry()
            if target_screen is not None
            else to_rect
        )

        if self._teleport_overlay_out is not None:
            with contextlib.suppress(Exception):
                self._teleport_overlay_out.close()
            self._teleport_overlay_out = None
        if self._teleport_overlay_in is not None:
            with contextlib.suppress(Exception):
                self._teleport_overlay_in.close()
            self._teleport_overlay_in = None

        def on_peak() -> None:
            if self._window.is_closing:
                return
            self._window.setGeometry(to_rect)
            wh = self._window.windowHandle()
            if wh is not None and target_screen is not None:
                wh.setScreen(target_screen)
            set_config_value(
                "window.position", {"x": to_rect.x(), "y": to_rect.y()}
            )
            set_config_value(
                "window.overlay_position",
                {"x": to_rect.x(), "y": to_rect.y()},
            )
            self._window.set_pose("idle")
            self._window.show()
            self._window.raise_()
            self._window.surge_ticks = 12
            try:
                from ..ui.speech_sfx import get_speech_sfx

                get_speech_sfx().play_teleport_drop()
            except Exception:
                pass
            self._window.update()

        def on_finished() -> None:
            self._teleport_overlay_out = None
            if self._window.is_closing:
                return
            self._window.set_pose("idle")
            self._window.show()
            self._window.raise_()
            self._window.update()
            if on_finished_callback is not None:
                on_finished_callback()

        self._window.set_pose("idle")
        self._window.hide()

        combined_screen_rect = (
            self._window.screen().geometry().united(screen_rect)
            if self._window.screen() is not None
            else screen_rect
        )

        self._teleport_overlay_out = TransitionOverlay(
            combined_screen_rect,
            to_rect,
            mode,
            target=self._window,
            on_peak=on_peak,
            target_point=from_rect.center(),
        )
        self._teleport_overlay_out.finished.connect(on_finished)
        self._teleport_overlay_out.start()
