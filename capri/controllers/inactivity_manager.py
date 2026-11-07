"""Управление неактивностью питомца и периодическими напоминаниями."""

from __future__ import annotations

import contextlib
import random
from collections.abc import Callable

from PySide6.QtCore import QObject, QRect, QTimer
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import QWidget

from ..effects.transition import TransitionOverlay
from ..integrations.system_control import (
    get_mouse_position,
    move_mouse_to_center,
)

INACTIVITY_TIMEOUT_MS = 5_000


class InactivityManager(QObject):
    """Контроллер скрытия и появления питомца по таймеру неактивности."""

    def __init__(
        self,
        main_window: QWidget,
        *,
        is_closing: Callable[[], bool] | None = None,
        on_wake_voice: Callable[[], None] | None = None,
        get_designated_screen: Callable[[], QScreen | None] | None = None,
    ) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._is_closing = is_closing or (lambda: False)
        self._on_wake_voice = on_wake_voice or (lambda: None)
        self._get_designated_screen = get_designated_screen

        self._transitioning = False
        self._transition_overlay: TransitionOverlay | None = None
        self._voice_was_listening = False
        self._paused = False
        self._pending_show_callbacks: list[Callable[[], None]] = []

        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.timeout.connect(self._hide_for_inactivity)
        self._timeout_ms = INACTIVITY_TIMEOUT_MS

    def set_timeout_ms(self, timeout_ms: int) -> None:
        self._timeout_ms = max(500, int(timeout_ms))
        if self._inactivity_timer.isActive():
            self.reset_timer()

    @property
    def is_paused(self) -> bool:
        return self._paused

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        if paused:
            self._inactivity_timer.stop()
        else:
            self.reset_timer()

    @property
    def is_transitioning(self) -> bool:
        return self._transitioning

    @property
    def current_target_widget(self) -> QWidget:
        return self._main_window

    def get_target_screen(self) -> QScreen:
        if self._get_designated_screen is not None:
            scr = self._get_designated_screen()
            if scr is not None:
                return scr

        target = self.current_target_widget
        wh = target.windowHandle()
        if wh is not None and wh.screen() is not None:
            return wh.screen()

        scr = target.screen()
        if scr is not None:
            return scr

        center = target.frameGeometry().center()
        for s in QGuiApplication.screens():
            if s.geometry().contains(center):
                return s

        return QGuiApplication.primaryScreen()

    def start(self) -> None:
        self._inactivity_timer.start(self._timeout_ms)

    def stop(self) -> None:
        self._inactivity_timer.stop()

    def reset_timer(self) -> None:
        if self._paused or self._is_closing():
            return
        if self._transitioning:
            return
        target = self.current_target_widget
        if not target.isVisible():
            self._start_show_transition()
            return
        self._inactivity_timer.stop()
        self._inactivity_timer.start(self._timeout_ms)

    def show_with_callback(
        self,
        callback: Callable[[], None],
        erratic: bool = False,
        target_pos: tuple[int, int] | None = None,
    ) -> None:
        if self._is_closing():
            return
        target = self.current_target_widget
        if target.isVisible():
            callback()
            return
        if self._paused or self._transitioning:
            return
        self._pending_show_callbacks.append(callback)
        self._start_show_transition(erratic=erratic, target_pos=target_pos)

    def relocate_randomly(self) -> None:
        target = self.current_target_widget
        screen = self.get_target_screen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        w = target.width()
        h = target.height()
        max_x = max(geo.left(), geo.right() - w)
        max_y = max(geo.top(), geo.bottom() - h)
        rand_x = random.randint(geo.left(), max_x)
        rand_y = random.randint(geo.top(), max_y)
        target.move(rand_x, rand_y)

    def relocate_overlay_randomly(self) -> None:
        self.relocate_randomly()

    def _hide_for_inactivity(self) -> None:
        if self._paused or self._is_closing() or self._transitioning:
            return

        if (
            hasattr(self._main_window, "is_speaking")
            and self._main_window.is_speaking
        ):
            self._inactivity_timer.start(500)
            return

        target = self.current_target_widget
        if not target.isVisible():
            return
        self._transitioning = True
        self._inactivity_timer.stop()
        screen = self.get_target_screen()
        screen_rect = (
            screen.geometry() if screen is not None else target.geometry()
        )
        overlay = TransitionOverlay(
            screen_rect, target.geometry(), "out", target=target
        )
        overlay.finished.connect(self._finish_hide_transition)
        self._transition_overlay = overlay
        overlay.start()

    def _start_show_transition(
        self,
        erratic: bool = False,
        target_pos: tuple[int, int] | None = None,
    ) -> None:
        self._transitioning = True
        screen = self.get_target_screen()
        target = self.current_target_widget
        if target_pos is not None:
            target.move(target_pos[0], target_pos[1])
        else:
            self.relocate_randomly()
        if hasattr(target, "set_pose"):
            target.set_pose("idle")
        target.hide()

        screen_rect = (
            screen.geometry() if screen is not None else target.geometry()
        )
        overlay = TransitionOverlay(
            screen_rect,
            target.geometry(),
            "erratic_in" if erratic else "in",
            target=target,
            on_peak=self._reveal_target_on_show_peak,
        )
        overlay.finished.connect(self._finish_show_transition)
        self._transition_overlay = overlay
        overlay.start()

    def _reveal_target_on_show_peak(self) -> None:
        target = self.current_target_widget
        target.show()
        target.raise_()

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
        self._inactivity_timer.start(self._timeout_ms)
        callbacks = self._pending_show_callbacks
        self._pending_show_callbacks = []
        for callback in callbacks:
            callback()

    def catch_mouse(
        self, on_pose_change: Callable[[str], None] | None = None
    ) -> str:
        cursor_pos = get_mouse_position()
        target = self.current_target_widget

        if on_pose_change is not None:
            on_pose_change("crouch")

        cursor_screen = None
        for scr in QGuiApplication.screens():
            if scr.geometry().contains(cursor_pos):
                cursor_screen = scr
                break
        if cursor_screen is None:
            cursor_screen = self.get_target_screen()

        target_screen = self.get_target_screen()
        target_screen_index = None
        for idx, scr in enumerate(QGuiApplication.screens()):
            if (
                scr.name() == target_screen.name()
                or scr.geometry() == target_screen.geometry()
            ):
                target_screen_index = idx
                break

        geo = target_screen.availableGeometry()

        flash_size = 140
        cursor_rect = QRect(
            cursor_pos.x() - flash_size // 2,
            cursor_pos.y() - flash_size // 2,
            flash_size,
            flash_size,
        )

        center_x = geo.left() + (geo.width() - target.width()) // 2
        center_y = geo.top() + (geo.height() - target.height()) // 2
        center_rect = QRect(
            center_x, center_y, target.width(), target.height()
        )
        target_center = center_rect.center()

        def move_mouse() -> None:
            with contextlib.suppress(Exception):
                move_mouse_to_center(
                    target_center, screen_index=target_screen_index
                )

        def on_teleport_finished() -> None:
            move_mouse()
            if on_pose_change is not None:
                on_pose_change("sit")

        self.teleport_from_cursor_to_center(
            target=target,
            cursor_rect=cursor_rect,
            center_rect=center_rect,
            cursor_screen_rect=cursor_screen.geometry(),
            target_screen_rect=target_screen.geometry(),
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
        cursor_screen_rect: QRect | None = None,
        target_screen_rect: QRect | None = None,
        on_materialize: Callable[[], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        if self._transition_overlay is not None:
            with contextlib.suppress(Exception):
                self._transition_overlay.close()
            self._transition_overlay = None

        self._transitioning = True
        self._inactivity_timer.stop()

        target_screen = self.get_target_screen()
        final_target_screen_rect = (
            target_screen_rect
            if target_screen_rect is not None
            else (
                target_screen.geometry()
                if target_screen is not None
                else center_rect
            )
        )
        final_cursor_screen_rect = (
            cursor_screen_rect
            if cursor_screen_rect is not None
            else final_target_screen_rect
        )

        center_point = center_rect.center()

        target.hide()

        def on_lightning_finished() -> None:
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
                self._inactivity_timer.start(self._timeout_ms)
                if on_finished is not None:
                    on_finished()

            overlay_in = TransitionOverlay(
                final_target_screen_rect,
                center_rect,
                "in",
                target=target,
                on_peak=on_in_peak,
            )
            overlay_in.finished.connect(on_in_finished)
            self._transition_overlay = overlay_in
            overlay_in.start()

        overlay_lightning = TransitionOverlay(
            final_cursor_screen_rect,
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
        if self._transition_overlay is not None:
            with contextlib.suppress(Exception):
                self._transition_overlay.close()
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
                self._inactivity_timer.start(self._timeout_ms)
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


MIN_REMINDER_INTERVAL_MS = 600_000
MAX_REMINDER_INTERVAL_MS = 3_600_000

REMINDER_PHRASES: tuple[str, ...] = (
    "Я всё ещё здесь. Не забывай про меня.",
    "Протокол одиночества активирован... Пошутила. Просто проверяю связь.",
    "Капри в сети. Может, поговорим?",
    "Эй, у тебя всё в порядке? Я на связи.",
    "Система скучает. Верни меня в кадр хоть на секунду.",
)


class PresenceReminder(QObject):
    """Периодический таймер напоминания о присутствии питомца."""

    def __init__(
        self,
        on_remind: Callable[[str], None],
        parent: QObject | None = None,
        min_interval_ms: int = MIN_REMINDER_INTERVAL_MS,
        max_interval_ms: int = MAX_REMINDER_INTERVAL_MS,
    ) -> None:
        super().__init__(parent)
        self._on_remind = on_remind
        self._active = False
        self._last_phrase: str | None = None
        self._min_interval_ms = max(5_000, min_interval_ms)
        self._max_interval_ms = max(self._min_interval_ms, max_interval_ms)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)
        self._suppressed = False

    def set_suppressed(self, suppressed: bool) -> None:
        self._suppressed = bool(suppressed)

    @property
    def min_interval_ms(self) -> int:
        return self._min_interval_ms

    @property
    def max_interval_ms(self) -> int:
        return self._max_interval_ms

    def set_interval_range(self, min_ms: int, max_ms: int) -> None:
        self._min_interval_ms = max(5_000, int(min_ms))
        self._max_interval_ms = max(self._min_interval_ms, int(max_ms))
        if self._active:
            self._schedule_next()

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def seconds_until_next(self) -> int | None:
        if not self._active or not self._timer.isActive():
            return None
        return max(0, round(self._timer.remainingTime() / 1000))

    def start(self) -> None:
        self._active = True
        self._schedule_next()

    def stop(self) -> None:
        self._active = False
        self._timer.stop()

    def _schedule_next(self) -> None:
        if not self._active:
            return
        self._timer.start(
            random.randint(self._min_interval_ms, self._max_interval_ms)
        )

    def _next_phrase(self) -> str:
        candidates = [
            p for p in REMINDER_PHRASES if p != self._last_phrase
        ]
        phrase = random.choice(candidates or list(REMINDER_PHRASES))
        self._last_phrase = phrase
        return phrase

    def _fire(self) -> None:
        if not self._active:
            return
        self._schedule_next()
        if not self._suppressed:
            self._on_remind(self._next_phrase())
