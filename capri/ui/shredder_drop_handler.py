"""Blackwall Drag & Drop file absorption and secure shredder delegate for CapriPet."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent

from ..core.settings import get_config_value
from ..integrations.data_shredder import (
    _is_critical_path,
    generate_shred_dialogue,
    shred_paths,
)
from .speech_sfx import get_speech_sfx

if TYPE_CHECKING:
    from .pet_window import CapriWindow


class ShredderDropHandler:
    """Делегат обработки перетаскивания и безвозвратного поглощения файлов Blackwall."""

    def __init__(self, window: CapriWindow | Any) -> None:
        self._window = window

    def handle_drag_enter(self, event: QDragEnterEvent) -> None:
        if not get_config_value("behavior.file_shredder_enabled", True):
            event.ignore()
            return

        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._window._target_acquired = True
            get_speech_sfx().play_target_acquired()
            self._window.update()
        else:
            event.ignore()

    def handle_drag_move(self, event: QDragMoveEvent) -> None:
        if not get_config_value("behavior.file_shredder_enabled", True):
            event.ignore()
            return

        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            if not self._window._target_acquired:
                self._window._target_acquired = True
                self._window.update()
        else:
            event.ignore()

    def handle_drag_leave(self, event: QDragLeaveEvent) -> None:
        self._window._target_acquired = False
        self._window.update()

    def handle_drop(self, event: QDropEvent) -> None:
        if not get_config_value("behavior.file_shredder_enabled", True):
            event.ignore()
            return

        self._window._target_acquired = False
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return

        event.acceptProposedAction()

        paths = [Path(url.toLocalFile()) for url in urls if url.isLocalFile()]
        if not paths:
            return

        # Check for critical paths
        has_blocked = any(_is_critical_path(p) for p in paths)
        if has_blocked:
            get_speech_sfx().play_lightning_strike()
            self._window._consume_ticks = 18
            self._window.update()
            dialogue = generate_shred_dialogue(None, blocked=True)
            self._window._speak(dialogue, hold_ms=4500)
            return

        # Trigger rogue AI annihilation effects immediately
        self._window._consume_ticks = 30
        self._window._surge_ticks = 24
        get_speech_sfx().play_lightning_strike()
        get_speech_sfx().play_data_rip()
        self._window.update()

        # Perform unrecoverable shredding
        metrics = shred_paths(paths)
        dialogue = generate_shred_dialogue(metrics)
        self._window._speak(dialogue, hold_ms=5000)
