from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QObject, QRect

from .glitch import GlitchBurstOverlay, GlitchManager
from .model_init_animation import ModelInitOverlay
from .session_animations import (
    SessionAnimationOverlay,
    play_session_animation,
)
from .transition import TransitionOverlay

if TYPE_CHECKING:
    from ..ui.pet_window import CapriWindow

class EffectsCoordinator(QObject):
    

    def __init__(self, window: CapriWindow) -> None:
        super().__init__(window)
        self._window = window
        self._glitches = GlitchManager(window)
        self._startup_overlay: TransitionOverlay | None = None
        self._model_init_overlay: ModelInitOverlay | None = None
        self._session_overlay: SessionAnimationOverlay | None = None
        self._burst_overlay: GlitchBurstOverlay | None = None

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
            try:
                self._burst_overlay.close()
                self._burst_overlay.deleteLater()
            except Exception:
                pass
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
            try:
                self._session_overlay.close()
            except Exception:
                pass
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
            try:
                self._model_init_overlay.close()
            except Exception:
                pass
            self._model_init_overlay = None

        overlay = ModelInitOverlay(self._window)
        self._model_init_overlay = overlay
        overlay.finished.connect(self._clear_model_init_overlay)
        overlay.start()
        return overlay

    def _clear_model_init_overlay(self) -> None:
        self._model_init_overlay = None

    def stop_all(self) -> None:
        
        self._glitches.stop()
        if self._burst_overlay is not None:
            try:
                self._burst_overlay.close()
                self._burst_overlay.deleteLater()
            except Exception:
                pass
            self._burst_overlay = None

        if self._model_init_overlay is not None:
            try:
                self._model_init_overlay.close()
            except Exception:
                pass
            self._model_init_overlay = None

        if self._session_overlay is not None:
            try:
                self._session_overlay.close()
            except Exception:
                pass
            self._session_overlay = None

        if self._startup_overlay is not None:
            try:
                self._startup_overlay.close()
            except Exception:
                pass
            self._startup_overlay = None
