from __future__ import annotations

import random
from typing import Callable

from PySide6.QtCore import QObject, QRect, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

from ..effects.transition import TransitionOverlay
from ..integrations.cursor import get_mouse_position, move_mouse_to_center
from ..ui.overlay_window import CapriOverlayWindow

INACTIVITY_TIMEOUT_MS = 5_000


class InactivityManager(QObject):
    """Управление бездействием, скрытием/показом и анимациями переходов между окнами."""

    def __init__(
        self,
        main_window: QWidget,
        get_overlay: Callable[[], CapriOverlayWindow | None],
        is_overlay_mode: Callable[[], bool],
        is_closing: Callable[[], bool],
        on_wake_voice: Callable[[], None],
    ) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._get_overlay = get_overlay
        self._is_overlay_mode = is_overlay_mode
        self._is_closing = is_closing
        self._on_wake_voice = on_wake_voice

        self._transitioning = False
        self._transition_overlay: TransitionOverlay | None = None
        self._voice_was_listening = False

        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.timeout.connect(self._hide_for_inactivity)

    @property
    def is_transitioning(self) -> bool:
        return self._transitioning

    @property
    def current_target_widget(self) -> QWidget:
        overlay = self._get_overlay()
        if self._is_overlay_mode() and overlay is not None:
            return overlay
        return self._main_window

    def start(self) -> None:
        self._inactivity_timer.start(INACTIVITY_TIMEOUT_MS)

    def stop(self) -> None:
        self._inactivity_timer.stop()

    def reset_timer(self) -> None:
        if self._is_closing():
            return
        if self._transitioning:
            return
        target = self.current_target_widget
        if not target.isVisible():
            self._start_show_transition()
            return
        self._inactivity_timer.stop()
        self._inactivity_timer.start(INACTIVITY_TIMEOUT_MS)

    def relocate_overlay_randomly(self) -> None:
        overlay = self._get_overlay()
        if overlay is None:
            return
        screen = overlay.screen()
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        w = overlay.width()
        h = overlay.height()
        max_x = max(geo.left(), geo.right() - w)
        max_y = max(geo.top(), geo.bottom() - h)
        rand_x = random.randint(geo.left(), max_x)
        rand_y = random.randint(geo.top(), max_y)
        overlay.move(rand_x, rand_y)

    def _hide_for_inactivity(self) -> None:
        if self._is_closing():
            return
        if self._transitioning:
            return
        target = self.current_target_widget
        if not target.isVisible():
            return
        self._transitioning = True
        self._inactivity_timer.stop()
        screen = target.screen()
        screen_rect = (
            screen.geometry() if screen is not None else target.geometry()
        )
        overlay = TransitionOverlay(
            screen_rect, target.geometry(), "out", target=target
        )
        overlay.finished.connect(self._finish_hide_transition)
        self._transition_overlay = overlay
        overlay.start()

    def _start_show_transition(self) -> None:
        self._transitioning = True
        if self._is_overlay_mode() and self._get_overlay() is not None:
            self.relocate_overlay_randomly()
        target = self.current_target_widget
        screen = target.screen()
        screen_rect = (
            screen.geometry() if screen is not None else target.geometry()
        )
        overlay = TransitionOverlay(
            screen_rect,
            target.geometry(),
            "in",
            target=target,
            on_peak=self._reveal_target_on_show_peak,
        )
        overlay.finished.connect(self._finish_show_transition)
        self._transition_overlay = overlay
        overlay.start()

    def _reveal_target_on_show_peak(self) -> None:
        overlay = self._get_overlay()
        if self._is_overlay_mode():
            self._main_window.hide()
            if overlay is not None:
                overlay.show()
                overlay.raise_()
        else:
            if overlay is not None:
                overlay.hide()
            self._main_window.show()
            self._main_window.raise_()

    def _finish_hide_transition(self) -> None:
        self._transitioning = False
        self._transition_overlay = None
        target = self.current_target_widget
        target.hide()

    def _finish_show_transition(self) -> None:
        self._transitioning = False
        self._transition_overlay = None
        self._reveal_target_on_show_peak()
        self._on_wake_voice()
        self._inactivity_timer.stop()
        self._inactivity_timer.start(INACTIVITY_TIMEOUT_MS)

    def switch_target(
        self, old_target: QWidget, new_target: QWidget
    ) -> None:
        if self._transition_overlay is not None:
            try:
                self._transition_overlay.close()
            except Exception:
                pass
            self._transition_overlay = None

        self._transitioning = True
        self._inactivity_timer.stop()

        old_screen = old_target.screen() or new_target.screen()
        old_screen_rect = (
            old_screen.geometry()
            if old_screen is not None
            else old_target.geometry()
        )

        def on_out_peak() -> None:
            old_target.hide()

        def on_out_finished() -> None:
            new_screen = new_target.screen()
            new_screen_rect = (
                new_screen.geometry()
                if new_screen is not None
                else new_target.geometry()
            )

            def on_in_peak() -> None:
                new_target.show()
                new_target.raise_()

            def on_in_finished() -> None:
                self._transitioning = False
                self._transition_overlay = None
                new_target.show()
                new_target.raise_()
                self._inactivity_timer.start(INACTIVITY_TIMEOUT_MS)

            overlay_in = TransitionOverlay(
                new_screen_rect,
                new_target.geometry(),
                "in",
                target=new_target,
                on_peak=on_in_peak,
            )
            overlay_in.finished.connect(on_in_finished)
            self._transition_overlay = overlay_in
            overlay_in.start()

        overlay_out = TransitionOverlay(
            old_screen_rect,
            old_target.geometry(),
            "out",
            target=old_target,
            on_peak=on_out_peak,
        )
        overlay_out.finished.connect(on_out_finished)
        self._transition_overlay = overlay_out
        overlay_out.start()

    def catch_mouse(
        self, on_pose_change: Callable[[str], None] | None = None
    ) -> str:
        """Вспышка у курсора, молнии в центр и появление Капри с курсором."""
        cursor_pos = get_mouse_position()
        target = self.current_target_widget

        if on_pose_change is not None:
            on_pose_change("crouch")

        screen = None
        for scr in QGuiApplication.screens():
            if scr.geometry().contains(cursor_pos):
                screen = scr
                break
        if screen is None:
            screen = target.screen() or QGuiApplication.primaryScreen()

        geo = screen.availableGeometry() if screen is not None else target.geometry()

        flash_size = 140
        cursor_rect = QRect(
            cursor_pos.x() - flash_size // 2,
            cursor_pos.y() - flash_size // 2,
            flash_size,
            flash_size,
        )

        center_x = geo.left() + (geo.width() - target.width()) // 2
        center_y = geo.top() + (geo.height() - target.height()) // 2
        center_rect = QRect(center_x, center_y, target.width(), target.height())

        def move_mouse() -> None:
            try:
                move_mouse_to_center()
            except Exception:
                pass

        def on_teleport_finished() -> None:
            move_mouse()
            if on_pose_change is not None:
                on_pose_change("sit")

        self.teleport_from_cursor_to_center(
            target=target,
            cursor_rect=cursor_rect,
            center_rect=center_rect,
            on_materialize=move_mouse,
            on_finished=on_teleport_finished,
        )

        self.reset_timer()
        return "Поймала мышку!"

    def teleport_from_cursor_to_center(
        self,
        target: QWidget,
        cursor_rect: QRect,
        center_rect: QRect,
        on_materialize: Callable[[], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        """Вспышка у курсора, молнии тянутся в центр, затем материализация Капри с курсором."""
        if self._transition_overlay is not None:
            try:
                self._transition_overlay.close()
            except Exception:
                pass
            self._transition_overlay = None

        self._transitioning = True
        self._inactivity_timer.stop()

        screen = target.screen() or QGuiApplication.primaryScreen()
        screen_rect = (
            screen.geometry() if screen is not None else center_rect
        )

        center_point = center_rect.center()

        # Капри скрыта до появления в центре
        target.hide()

        def on_lightning_finished() -> None:
            # Молнии дотянулись до центра -> перемещаем Капри в центр и запускаем материализацию
            target.setGeometry(center_rect)

            def on_in_peak() -> None:
                target.show()
                target.raise_()
                if on_materialize is not None:
                    on_materialize()

            def on_in_finished() -> None:
                self._transitioning = False
                self._transition_overlay = None
                target.show()
                target.raise_()
                self._inactivity_timer.start(INACTIVITY_TIMEOUT_MS)
                if on_finished is not None:
                    on_finished()

            overlay_in = TransitionOverlay(
                screen_rect,
                center_rect,
                "in",
                target=target,
                on_peak=on_in_peak,
            )
            overlay_in.finished.connect(on_in_finished)
            self._transition_overlay = overlay_in
            overlay_in.start()

        # Шаг 1: Вспышка около курсора и молнии, вытягивающиеся в центр экрана
        overlay_lightning = TransitionOverlay(
            screen_rect,
            cursor_rect,
            "lightning_to_point",
            target=None,
            target_point=center_point,
        )
        overlay_lightning.finished.connect(on_lightning_finished)
        self._transition_overlay = overlay_lightning
        overlay_lightning.start()

    def teleport_target(
        self,
        target: QWidget,
        from_rect: QRect,
        to_rect: QRect,
        on_peak_in: Callable[[], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        """Телепортация виджета из from_rect в to_rect с пиксельными глитчами и молниями."""
        if self._transition_overlay is not None:
            try:
                self._transition_overlay.close()
            except Exception:
                pass
            self._transition_overlay = None

        self._transitioning = True
        self._inactivity_timer.stop()

        screen = target.screen() or QGuiApplication.primaryScreen()
        screen_rect = (
            screen.geometry() if screen is not None else from_rect
        )

        def on_out_peak() -> None:
            target.hide()

        def on_out_finished() -> None:
            # Перемещаем виджет в целевую точку
            target.setGeometry(to_rect)

            def on_in_peak() -> None:
                target.show()
                target.raise_()
                if on_peak_in is not None:
                    on_peak_in()

            def on_in_finished() -> None:
                self._transitioning = False
                self._transition_overlay = None
                target.show()
                target.raise_()
                self._inactivity_timer.start(INACTIVITY_TIMEOUT_MS)
                if on_finished is not None:
                    on_finished()

            overlay_in = TransitionOverlay(
                screen_rect,
                to_rect,
                "in",
                target=target,
                on_peak=on_in_peak,
            )
            overlay_in.finished.connect(on_in_finished)
            self._transition_overlay = overlay_in
            overlay_in.start()

        overlay_out = TransitionOverlay(
            screen_rect,
            from_rect,
            "out",
            target=target,
            on_peak=on_out_peak,
        )
        overlay_out.finished.connect(on_out_finished)
        self._transition_overlay = overlay_out
        overlay_out.start()

