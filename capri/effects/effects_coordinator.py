"""Координатор визуальных спецэффектов и анимаций питомца Capri."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRect

from .glitch import GlitchBurstOverlay, GlitchManager
from .intro_breach_overlay import IntroBreachOverlay
from .melting_screen import MeltingScreenOverlay
from .model_init_animation import ModelInitOverlay
from .session_animations import (
    SessionAnimationOverlay,
    play_session_animation,
)
from .transition import TransitionOverlay

if TYPE_CHECKING:
    from ..ui.pet_window import CapriWindow


class EffectsCoordinator(QObject):
    """Координатор жизненного цикла визуальных эффектов, глитчей и оверлеев."""

    def __init__(self, window: CapriWindow) -> None:
        super().__init__(window)
        self._window = window
        self._glitches = GlitchManager(window)
        self._startup_overlay: TransitionOverlay | None = None
        self._model_init_overlay: ModelInitOverlay | None = None
        self._session_overlay: SessionAnimationOverlay | None = None
        self._burst_overlay: GlitchBurstOverlay | None = None
        self._intro_breach_overlay: IntroBreachOverlay | None = None
        self._melting_overlay: MeltingScreenOverlay | None = None

    @property
    def glitches(self) -> GlitchManager:
        return self._glitches

    @property
    def is_glitch_enabled(self) -> bool:
        return self._glitches.is_enabled

    @property
    def glitch_intensity(self) -> str:
        return self._glitches.intensity

    def set_glitch_intensity(self, intensity: str) -> None:
        self._glitches.set_intensity(intensity)

    def toggle_glitches(self) -> bool:
        return self._glitches.toggle()

    def glitch_burst(
        self,
        rect: QRect,
        duration_ms: int = 1400,
        intensity: str = "strong",
        on_finished: Callable[[], None] | None = None,
    ) -> GlitchBurstOverlay | None:

        if getattr(self._window, "is_closing", False):
            return None

        if self._burst_overlay is not None:
            with contextlib.suppress(Exception):
                self._burst_overlay.close()
                self._burst_overlay.deleteLater()
            self._burst_overlay = None

        overlay = GlitchBurstOverlay(
            rect,
            duration_ms=duration_ms,
            intensity=intensity,
            parent=None,
        )
        self._burst_overlay = overlay

        def _cleanup() -> None:
            if self._burst_overlay is overlay:
                self._burst_overlay = None
            if on_finished is not None:
                on_finished()

        overlay.finished.connect(_cleanup)
        overlay.start()
        return overlay

    def play_session(self, action: str) -> SessionAnimationOverlay | None:

        if getattr(self._window, "is_closing", False):
            return None

        if self._session_overlay is not None:
            with contextlib.suppress(Exception):
                self._session_overlay.close()
            self._session_overlay = None

        overlay = play_session_animation(self._window, action)
        self._session_overlay = overlay
        overlay.finished.connect(self._clear_session_overlay)
        return overlay

    def _clear_session_overlay(self) -> None:
        self._session_overlay = None

    def start_model_init(self) -> ModelInitOverlay | None:

        if getattr(self._window, "is_closing", False):
            return None

        if self._model_init_overlay is not None:
            with contextlib.suppress(Exception):
                self._model_init_overlay.close()
            self._model_init_overlay = None

        overlay = ModelInitOverlay(self._window)
        self._model_init_overlay = overlay
        overlay.finished.connect(self._clear_model_init_overlay)
        overlay.start()
        return overlay

    def _clear_model_init_overlay(self) -> None:
        self._model_init_overlay = None

    def play_intro_breach(
        self, on_finished: Callable[[], None] | None = None
    ) -> IntroBreachOverlay | None:
        if getattr(self._window, "is_closing", False):
            return None

        if self._intro_breach_overlay is not None:
            with contextlib.suppress(Exception):
                self._intro_breach_overlay.close()
            self._intro_breach_overlay = None

        self._window.setWindowOpacity(0.0)
        self._window.hide()

        screen = self._window.screen()
        sprite = getattr(self._window, "current_pixmap", None)
        overlay = IntroBreachOverlay(
            screen=screen,
            sprite_pixmap=sprite,
            on_finished=on_finished,
        )
        self._intro_breach_overlay = overlay
        overlay.finished.connect(self._clear_intro_breach_overlay)
        overlay.start()
        return overlay

    def _clear_intro_breach_overlay(self) -> None:
        self._intro_breach_overlay = None

    def play_melting_screen(
        self,
        duration_ms: int = 1400,
        on_finished: Callable[[], None] | None = None,
    ) -> MeltingScreenOverlay | None:
        if getattr(self._window, "is_closing", False):
            return None

        if self._melting_overlay is not None:
            with contextlib.suppress(Exception):
                self._melting_overlay.close()
                self._melting_overlay.deleteLater()
            self._melting_overlay = None

        target_screen = self._window.screen() if hasattr(self._window, "screen") else None
        overlay = MeltingScreenOverlay(
            screen=target_screen,
            duration_ms=duration_ms,
        )
        self._melting_overlay = overlay

        def _cleanup() -> None:
            if self._melting_overlay is overlay:
                self._melting_overlay = None
            if on_finished is not None:
                on_finished()

        overlay.finished.connect(_cleanup)
        overlay.start()
        return overlay

    def stop_all(self) -> None:

        self._glitches.stop()
        if self._melting_overlay is not None:
            with contextlib.suppress(Exception):
                self._melting_overlay.close()
                self._melting_overlay.deleteLater()
            self._melting_overlay = None
        if self._burst_overlay is not None:
            with contextlib.suppress(Exception):
                self._burst_overlay.close()
                self._burst_overlay.deleteLater()
            self._burst_overlay = None

        if self._model_init_overlay is not None:
            with contextlib.suppress(Exception):
                self._model_init_overlay.close()
            self._model_init_overlay = None

        if self._session_overlay is not None:
            with contextlib.suppress(Exception):
                self._session_overlay.close()
            self._session_overlay = None

        if self._intro_breach_overlay is not None:
            with contextlib.suppress(Exception):
                self._intro_breach_overlay.close()
            self._intro_breach_overlay = None

        if self._startup_overlay is not None:
            with contextlib.suppress(Exception):
                self._startup_overlay.close()
            self._startup_overlay = None
