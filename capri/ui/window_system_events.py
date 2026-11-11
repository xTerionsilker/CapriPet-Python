"""System power and session state transition delegate for CapriWindow."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from ..core.settings import set_config_value

if TYPE_CHECKING:
    from .pet_window import CapriWindow


class WindowSystemEventsHandler:
    """Делегат обработки системных событий питания, блокировки и быстрого завершения."""

    def __init__(self, window: CapriWindow | Any) -> None:
        self._window = window

    def handle_system_suspend(self) -> None:
        self.fast_terminate()

    def handle_system_shutdown(self) -> None:
        self.fast_terminate()

    def handle_session_lock(self) -> None:
        if getattr(self._window, "_closing", False):
            return
        self._window._orchestrator.pause()
        self._window._glitch_timer.stop()

    def handle_session_unlock(self) -> None:
        if getattr(self._window, "_closing", False):
            return
        self._window._glitch_timer.start()
        self._window._orchestrator.resume()
        self._window.trigger_pose_transition()

    def fast_terminate(self) -> None:
        if getattr(self._window, "_closing", False):
            return
        self._window._closing = True
        with contextlib.suppress(Exception):
            pos = self._window.pos()
            set_config_value(
                "window.position", {"x": pos.x(), "y": pos.y()}
            )
            set_config_value(
                "window.overlay_position", {"x": pos.x(), "y": pos.y()}
            )
        self._window._orchestrator.stop()
        self._window._effects.stop_all()
        self._window._glitch_timer.stop()
        self._window._finalize_quit()
