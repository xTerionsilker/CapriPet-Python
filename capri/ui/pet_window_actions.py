"""Делегат действий и вспомогательных операций окна питомца Capri."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtMultimedia import QAudioDevice

from ..core.settings import (
    ACTIVITY_TIMEOUT_OPTIONS_MS,
    get_config_value,
    set_config_value,
)
from .speech import has_active_speech
from .speech_sfx import get_speech_sfx

if TYPE_CHECKING:
    from ..effects.effects_coordinator import EffectsCoordinator
    from .pet_window import CapriWindow
    from .speech import SpeechWindow


class PetWindowActionDelegate:
    """Делегат настроек и прикладных действий CapriWindow."""

    def __init__(self, window: CapriWindow) -> None:
        self._window = window

    @property
    def commands(self) -> Any:
        return self._window._orchestrator.commands

    @property
    def input_flow(self) -> Any:
        return self._window._orchestrator.flow

    @property
    def voice(self) -> Any:
        return getattr(self._window._orchestrator, "voice", None)
    @property
    def glitches(self) -> Any:
        return getattr(self._window._effects, "glitches", None)

    @property
    def effects(self) -> EffectsCoordinator:
        return self._window._effects

    @property
    def volume_percent(self) -> int:
        return self._window._volume_percent

    @property
    def scale_percent(self) -> int:
        return self._window._sprite_manager.scale_percent

    @property
    def selected_microphone(self) -> QAudioDevice | None:
        return self._window._orchestrator.voice_coordinator.selected_device

    @property
    def is_speaking(self) -> bool:
        return (
            self._window._speaking
            or has_active_speech()
            or (
                self._window._speech is not None
                and self._window._speech.isVisible()
            )
        )

    @property
    def glitches_enabled(self) -> bool:
        return self._window._effects.is_glitch_enabled

    @property
    def glitch_intensity(self) -> str:
        return self._window._effects.glitch_intensity

    @property
    def reminders_enabled(self) -> bool:
        return self._window._orchestrator.reminders_enabled

    @property
    def reminder_interval_range(self) -> tuple[int, int]:
        return (
            self._window._orchestrator.reminder.min_interval_ms,
            self._window._orchestrator.reminder.max_interval_ms,
        )
    @property
    def activity_timeout_seconds(self) -> int:
        return self._window._activity_timeout_seconds

    @property
    def game_suppression_enabled(self) -> bool:
        return self._window._game_detector.suppression_enabled

    @property
    def process_monitoring_enabled(self) -> bool:
        orchestrator = getattr(self._window, "_orchestrator", None)
        if orchestrator and hasattr(orchestrator, "process_monitoring_enabled"):
            return bool(orchestrator.process_monitoring_enabled)
        return bool(get_config_value("telemetry.process_monitoring_enabled", True))

    def get_designated_screen(self) -> QScreen | None:
        if self._window._designated_screen_name:
            for scr in QGuiApplication.screens():
                if scr.name() == self._window._designated_screen_name:
                    return scr
        return self._window.screen() or QGuiApplication.primaryScreen()

    def set_designated_screen(self, screen: QScreen) -> None:
        self._window._designated_screen_name = screen.name()
        set_config_value("screen.designated_screen", screen.name())

        geo = screen.availableGeometry()
        wh = self._window.windowHandle()
        if wh is not None:
            wh.setScreen(screen)

        cx = geo.left() + (geo.width() - self._window.width()) // 2
        cy = geo.top() + (geo.height() - self._window.height()) // 2
        self._window.move(cx, cy)
        set_config_value("window.position", {"x": cx, "y": cy})
        set_config_value("window.overlay_position", {"x": cx, "y": cy})
        self._window._orchestrator.inactivity.reset_timer()
        self.speak(f"Перепрыгнула на монитор: {screen.name()}!")

    def set_designated_microphone(
        self, device: QAudioDevice | None
    ) -> None:
        self._window._orchestrator.voice_coordinator.set_device(device)
        desc = (
            device.description() if device and not device.isNull() else ""
        )
        set_config_value(
            "audio.designated_microphone", desc if desc else None
        )
        name = desc if desc else "По умолчанию"
        self.speak(f"Слушаю тебя через: {name}")


    def set_speech_sound_enabled(self, enabled: bool) -> None:
        get_speech_sfx().set_speech_sound_enabled(enabled)
        set_config_value("audio.speech_sound_enabled", bool(enabled))
        status = "врублен" if enabled else "заглушен"
        self.speak(f"Голосовой синтез: {status}")

    def set_effects_sound_enabled(self, enabled: bool) -> None:
        get_speech_sfx().set_effects_sound_enabled(enabled)
        set_config_value("audio.effects_sound_enabled", bool(enabled))
        status = "врублены" if enabled else "заглушены"
        self.speak(f"Кибер-эффекты: {status}")

    def set_master_volume(self, percent: int) -> None:
        if percent not in (25, 50, 75, 100):
            return
        if self._window._volume_percent == percent:
            return
        self._window._volume_percent = percent
        get_speech_sfx().set_volume(percent / 100.0)
        set_config_value("audio.volume", percent)
        self.speak(f"Громкость выкручена на: {percent}%!")

    def set_glitch_intensity(self, intensity: str) -> None:
        self._window._effects.set_glitch_intensity(intensity)
        set_config_value("effects.glitch_intensity", intensity)

    def set_activity_timeout(self, seconds: int) -> None:
        timeout_ms = int(seconds) * 1000
        if timeout_ms not in ACTIVITY_TIMEOUT_OPTIONS_MS:
            return
        self._window._activity_timeout_seconds = timeout_ms // 1000
        set_config_value("behavior.inactivity_timeout_ms", timeout_ms)
        self._window._orchestrator.inactivity.set_timeout_ms(timeout_ms)
        self.speak(f"Время в эфире: {seconds} с (потом прячусь)")
    def set_sprite_scale(self, percent: int) -> None:
        if self._window._sprite_manager.set_sprite_scale(percent):
            self.speak(f"Масштаб проекции: {percent}%!")

    def set_reminders_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if self._window._orchestrator.reminders_enabled == enabled:
            return
        self._window._orchestrator.reminders_enabled = enabled
        set_config_value("behavior.reminders_enabled", enabled)
        if enabled:
            self._window._orchestrator.reminder.start()
            self.speak("Буду доставать тебя напоминаниями!")
        else:
            self._window._orchestrator.reminder.stop()
            self.speak("Ладно, помолчу в тряпочку.")

    def set_reminder_interval_range(
        self, min_ms: int, max_ms: int
    ) -> None:
        self._window._orchestrator.reminder.set_interval_range(
            min_ms, max_ms
        )
        set_config_value(
            "behavior.reminder_min_interval_ms",
            self._window._orchestrator.reminder.min_interval_ms,
        )
        set_config_value(
            "behavior.reminder_max_interval_ms",
            self._window._orchestrator.reminder.max_interval_ms,
        )

    def set_pose(self, pose: str) -> None:
        changed = self._window._sprite_manager.set_pose(pose)
        if changed:
            self._window._pose_transition_ticks = 6
            self._window.surge_ticks = max(self._window.surge_ticks, 6)

    def set_pose_image(self, pose_name: str, path: Path) -> None:
        self._window._sprite_manager.set_pose_image(pose_name, path)

    def speak(
        self, text: str, hold_ms: int | None = None
    ) -> SpeechWindow | None:
        return self._window._speak(text, hold_ms)
    def toggle_glitches(self) -> str:
        return self._window._toggle_glitches()

    def process_input(self, text: str) -> str:
        return self._window._orchestrator.flow.handle(text)

    def toggle_voice(self) -> str:
        return self._window._orchestrator.voice_coordinator.toggle_voice()

    def set_discord_enabled(self, enabled: bool) -> None:
        self._window._orchestrator.set_discord_enabled(enabled)
        status = "врублено" if enabled else "вырублено"
        self.speak(f"Хвастаюсь в Discord: {status}")

    def show_context_menu(self, pos: QPoint) -> None:
        self._window._orchestrator.inactivity.set_paused(True)
        try:
            from .context_menu_window import CyberContextMenuWindow

            dialog = getattr(self._window, "_context_menu_dialog", None)
            if (
                not isinstance(dialog, CyberContextMenuWindow)
                or not dialog.isVisible()
            ):
                dialog = CyberContextMenuWindow(self._window)
                self._window._context_menu_dialog = dialog
                dialog.exec()
        finally:
            self._window._orchestrator.inactivity.set_paused(False)

    def activate_command_mode(self) -> None:
        if self._window.is_closing:
            return

        if self._window._orchestrator.inactivity.is_transitioning:
            inactivity = self._window._orchestrator.inactivity
            if inactivity.transition_overlay is not None:
                inactivity.transition_overlay.close()
                inactivity.transition_overlay = None
            inactivity.transitioning = False

        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        self._window._orchestrator.inactivity.reset_timer()

        self._window._orchestrator.voice_coordinator.wake_if_needed()
        self._window._orchestrator.voice_coordinator.arm()

    def trigger_intro_breach(self) -> None:
        self._window.trigger_intro_breach()

    def set_game_suppression_enabled(self, enabled: bool) -> None:
        set_config_value("game_mode.suppression_enabled", enabled)
        self._window._game_detector.set_enabled(enabled)

    def set_process_monitoring_enabled(self, enabled: bool) -> None:
        orchestrator = getattr(self._window, "_orchestrator", None)
        if orchestrator and hasattr(orchestrator, "set_process_monitoring_enabled"):
            orchestrator.set_process_monitoring_enabled(enabled)
        else:
            set_config_value("telemetry.process_monitoring_enabled", enabled)
