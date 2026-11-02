from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QObject, QTimer
from PySide6.QtMultimedia import QAudioDevice

from ..audio.recognizer import preload_model_async
from ..audio.voice import VoiceInput
from ..core.settings import get_config_value, set_config_value
from ..core.wake_word import VOICE_COMMAND_WINDOW_MS, command_after_trigger
from .voice_hud import CyberVoiceHud

if TYPE_CHECKING:
    from .pet_window import CapriWindow

WAKE_LINES = (
    "Что?",
    "Слушаю.",
    "Я здесь.",
    "Да?",
    "Говори.",
)


class VoiceCoordinator(QObject):
    """Координирует работу голосового ввода, таймеров триггер-фразы и HUD."""

    def __init__(
        self,
        window: CapriWindow,
        on_command_ready: Callable[[str], None],
        speak_fn: Callable[[str], None],
    ) -> None:
        super().__init__(window)
        self._window = window
        self._on_command_ready = on_command_ready
        self._speak_fn = speak_fn

        self._hud: CyberVoiceHud | None = None
        self._voice_armed_until = 0.0

        if get_config_value("audio.voice_enabled", True):
            preload_model_async()

        self._voice = VoiceInput(always_on=False)
        self._voice.recognized.connect(self._on_voice_text)
        self._voice.partial_recognized.connect(self._on_partial_voice_text)
        self._voice.failed.connect(self._speak_fn)

        self._voice_window_timer = QTimer(self)
        self._voice_window_timer.setSingleShot(True)
        self._voice_window_timer.timeout.connect(self._on_voice_window_expired)

    @property
    def voice(self) -> VoiceInput:
        return self._voice

    @property
    def is_listening(self) -> bool:
        return self._voice.is_listening

    @property
    def is_busy(self) -> bool:
        return self._voice.is_busy

    @property
    def selected_device(self) -> QAudioDevice | None:
        return self._voice.selected_device

    def set_device(self, device: QAudioDevice | None) -> None:
        self._voice.set_device(device)

    def start_if_enabled(self) -> None:
        if get_config_value("audio.voice_enabled", True):
            self._voice.start()

    def wake_if_needed(self) -> None:
        if get_config_value("audio.voice_enabled", True) and not self._voice.is_listening and not self._voice.is_busy:
            self._voice.start()

    def toggle_voice(self) -> str:
        if self._voice.is_busy:
            return "Подождите, идёт распознавание."
        if self._voice.is_listening:
            self._voice.stop()
            set_config_value("audio.voice_enabled", False)
            return "Голосовой ввод отключён."
        else:
            preload_model_async()
            self._voice.start()
            set_config_value("audio.voice_enabled", True)
            if self._voice.is_listening:
                return "Слушаю. Скажи «Капри» и команду."
            return "Микрофон недоступен."

    def ensure_hud(self) -> CyberVoiceHud:
        if self._hud is None:
            self._hud = CyberVoiceHud(self._window)
        return self._hud

    def handle_awaiting_reply_changed(self, awaiting: bool) -> None:
        self._voice.set_armed(awaiting or self.is_armed)
        if awaiting:
            hud = self.ensure_hud()
            hud.show_hud(status="WAITING_ARGUMENT", mode="AWAITING_INPUT")
        else:
            if not self.is_armed:
                if self._hud is not None:
                    self._hud.hide_hud(delay_ms=400)

    @property
    def is_armed(self) -> bool:
        return time.monotonic() < self._voice_armed_until

    def _arm(self) -> None:
        self._voice_armed_until = time.monotonic() + VOICE_COMMAND_WINDOW_MS / 1000
        self._voice_window_timer.start(VOICE_COMMAND_WINDOW_MS)
        self._voice.set_armed(True)
        hud = self.ensure_hud()
        hud.show_hud(status="LISTENING_COMMAND", mode="TRIGGER_DETECTED")
        self._speak_fn(random.choice(WAKE_LINES))

    def _disarm(self) -> None:
        self._voice_armed_until = 0.0
        self._voice_window_timer.stop()
        self._voice.set_armed(False)
        if not self._window.input_flow.awaiting_reply:
            if self._hud is not None:
                self._hud.hide_hud(delay_ms=2200)

    def _on_voice_window_expired(self) -> None:
        self._voice_armed_until = 0.0
        self._voice.set_armed(False)
        if not self._window.input_flow.awaiting_reply:
            if self._hud is not None:
                self._hud.hide_hud(delay_ms=300)

    def _on_partial_voice_text(self, partial_text: str) -> None:
        """Отображает частичный текст в HUD в реальном времени, если бот активен."""
        if not partial_text:
            return
        if self.is_armed or self._window.input_flow.awaiting_reply:
            hud = self.ensure_hud()
            hud.set_recognized_text(partial_text, keep_ms=1500)

    def _resolve_command(self, text: str) -> str | None:
        command = command_after_trigger(text)
        if command is not None:
            return command
        if self._window.input_flow.awaiting_reply:
            return text.strip()
        if self.is_armed:
            return text.strip()
        return None

    def _on_voice_text(self, text: str) -> None:
        command = self._resolve_command(text)
        if command is None:
            return

        self._window.inactivity_manager.reset_timer()

        if self.is_armed or self._window.input_flow.awaiting_reply:
            hud = self.ensure_hud()
            hud.set_recognized_text(text, keep_ms=2500)

        if command:
            self._disarm()
            self._on_command_ready(command)
            return

        self._arm()
