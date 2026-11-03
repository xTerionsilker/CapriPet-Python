from __future__ import annotations

import time
from typing import Any, Callable

from PySide6.QtCore import QObject

from ..audio.recognizer import get_model_info
from ..commands import CommandContext, register_default_commands
from ..commands.registry import CommandRegistry
from ..controllers.action_bridge import ActionBridge
from ..controllers.inactivity_manager import InactivityManager
from ..controllers.presence_reminder import PresenceReminder
from ..core.input_flow import InputFlow, _parse_selected_number
from ..core.settings import ACTIVITY_TIMEOUT_OPTIONS_MS, get_config_value, set_config_value
from ..effects.session_animations import (
    SessionAnimationOverlay,
    play_session_animation,
)
from ..integrations.app_launcher import launch_application
from ..integrations.process_manager import kill_process_group
from ..integrations.window_tracker import get_active_window_rect
from ..ui.placement import pick_adjacent_position
from ..ui.voice_coordinator import VoiceCoordinator


class PetOrchestrator(QObject):
    """Оркестратор бизнес-логики: связывает команды, фоновые интеграции и UI."""

    def __init__(self, window: Any) -> None:
        super().__init__(window)
        self._window = window
        self._started_at = time.monotonic()
        self._session_overlay: SessionAnimationOverlay | None = None


        self.commands = CommandRegistry()
        self.flow = InputFlow(self.commands, self._window)


        self.actions = ActionBridge(self)
        self._connect_action_signals()


        self.voice_coordinator = VoiceCoordinator(
            self._window,
            on_command_ready=self.handle_command,
            speak_fn=self._window.speak,
        )
        self.flow.awaiting_reply_changed.connect(
            self.voice_coordinator.handle_awaiting_reply_changed
        )


        self.inactivity = InactivityManager(
            main_window=self._window,
            is_closing=lambda: getattr(self._window, "is_closing", False),
            on_wake_voice=self.voice_coordinator.wake_if_needed,
            get_designated_screen=self._window.get_designated_screen,
        )
        self._init_inactivity_settings()


        min_remind_ms = int(get_config_value("behavior.reminder_min_interval_ms", 600_000))
        max_remind_ms = int(get_config_value("behavior.reminder_max_interval_ms", 3_600_000))
        self.reminder = PresenceReminder(
            self._on_reminder,
            self._window,
            min_interval_ms=min_remind_ms,
            max_interval_ms=max_remind_ms,
        )
        self._reminders_enabled = bool(
            get_config_value("behavior.reminders_enabled", True)
        )
        if self._reminders_enabled:
            self.reminder.start()

        self._register_commands()

    def _connect_action_signals(self) -> None:
        self.actions.speech_requested.connect(self._window.speak)
        self.actions.session_animation_requested.connect(
            self._on_session_animation_requested
        )
        self.actions.ai_started.connect(self._on_ai_talking_start)
        self.actions.ai_finished.connect(self._on_ai_talking_end)
        self.actions.youtube_results_ready.connect(
            self._on_youtube_results_ready
        )
        self.actions.launch_app_results_ready.connect(
            self._on_launch_app_results_ready
        )
        self.actions.kill_app_results_ready.connect(
            self._on_kill_app_results_ready
        )
        self.actions.update_check_finished.connect(
            self._on_update_check_finished
        )

    def _init_inactivity_settings(self) -> None:
        inactivity_ms = get_config_value(
            "behavior.inactivity_timeout_ms", ACTIVITY_TIMEOUT_OPTIONS_MS[0]
        )
        try:
            inactivity_ms = int(inactivity_ms)
        except (ValueError, TypeError):
            inactivity_ms = ACTIVITY_TIMEOUT_OPTIONS_MS[0]
        if inactivity_ms not in ACTIVITY_TIMEOUT_OPTIONS_MS:
            inactivity_ms = ACTIVITY_TIMEOUT_OPTIONS_MS[0]
        self.inactivity.set_timeout_ms(inactivity_ms)

    def start(self) -> None:
        self.voice_coordinator.start_if_enabled()
        self.inactivity.start()

    def stop(self) -> None:
        self.inactivity.stop()
        self.reminder.stop()
        self.voice_coordinator.voice.cancel()
        if self._session_overlay is not None:
            try:
                self._session_overlay.close()
            except Exception:
                pass
            self._session_overlay = None

    def handle_command(self, text: str) -> None:
        result = self.flow.handle(text)
        self._window.speak(result)

    def _register_commands(self) -> None:
        context = CommandContext(
            speak=self._window.speak,
            trigger_glitches=self._window.toggle_glitches,
            toggle_voice=self.voice_coordinator.toggle_voice,
            locate_mouse=self._locate_mouse,
            set_pose=self._window.set_pose,
            get_config=get_config_value,
            set_config=set_config_value,
            expect_reply=self.flow.expect_reply,
            action_bridge=self.actions,
            debug_info=self.debug_info,
        )
        self.commands.set_context(context)
        register_default_commands(self.commands)

    def debug_info(self) -> dict[str, object]:
        return {
            "vosk": get_model_info(),
            "next_reminder_seconds": self.reminder.seconds_until_next,
            "uptime_seconds": time.monotonic() - self._started_at,
        }

    def _locate_mouse(self) -> str:
        return self.inactivity.catch_mouse(
            on_pose_change=self._window.set_pose
        )

    def _on_reminder(self, phrase: str) -> None:
        if self._window.is_closing or self._window.is_speaking or self.inactivity.is_paused:
            return


        target_rect = get_active_window_rect()
        effects = getattr(self._window, "effects", None)

        def _after_glitch_or_direct() -> None:
            if self._window.is_closing:
                return

            if target_rect is not None and target_rect.isValid():

                screen = self.inactivity.get_target_screen()
                screen_area = screen.geometry() if screen is not None else target_rect
                pet_w = self._window.width()
                pet_h = self._window.height()

                target_x, target_y, _ = pick_adjacent_position(
                    screen_area,
                    target_rect,
                    pet_w,
                    pet_h,
                    gap=24,
                )

                if self._window.isVisible():

                    teleport_ctrl = getattr(self._window, "_teleport", None)
                    if teleport_ctrl is not None:
                        from PySide6.QtCore import QPoint
                        teleport_ctrl.teleport_to_point(
                            QPoint(target_x + pet_w // 2, target_y + pet_h // 2)
                        )
                    else:
                        self._window.move(target_x, target_y)
                    self._window.speak(phrase)
                else:

                    self._window.move(target_x, target_y)
                    self.inactivity.show_with_callback(lambda: self._window.speak(phrase))
            else:
                if self._window.isVisible():
                    self._window.speak(phrase)
                else:
                    self.inactivity.show_with_callback(lambda: self._window.speak(phrase))


        if effects is not None and target_rect is not None and target_rect.isValid():
            effects.glitch_burst(
                target_rect,
                duration_ms=1300,
                intensity="strong",
                on_finished=_after_glitch_or_direct,
            )
        else:
            _after_glitch_or_direct()

    def _on_ai_talking_start(self) -> None:
        self._window.surge_ticks = max(self._window.surge_ticks, 24)
        self._window.set_pose("stay")

    def _on_ai_talking_end(self) -> None:
        self._window.surge_ticks = max(self._window.surge_ticks, 8)
        self._window.set_pose("sit")

    def _on_session_animation_requested(self, action: str) -> None:
        if self._window.is_closing:
            return
        if self._session_overlay is not None:
            try:
                self._session_overlay.close()
            except Exception:
                pass
            self._session_overlay = None

        overlay = play_session_animation(self._window, action)
        self._session_overlay = overlay
        overlay.finished.connect(
            lambda: self._forget_session_overlay(overlay)
        )

    def _forget_session_overlay(self, overlay: SessionAnimationOverlay) -> None:
        if self._session_overlay is overlay:
            self._session_overlay = None

    def _on_youtube_results_ready(self, videos: list[dict[str, str]]) -> None:
        if not videos or self._window.is_closing:
            return

        def _on_choice(text: str) -> str:
            choice = _parse_selected_number(text, max_number=len(videos))
            if choice is None:
                return "Не поняла номер. Поиск отменён."
            selected = videos[choice - 1]
            import webbrowser
            webbrowser.open(selected["url"])
            return f"Включаю #{choice}: {selected['title']}"

        lines = [
            f"{i}. {v['title'][:32]}…" if len(v['title']) > 32 else f"{i}. {v['title']}"
            for i, v in enumerate(videos, 1)
        ]
        prompt = "\n".join(lines) + "\nСкажи номер (1–5)"
        self.flow.expect_reply(_on_choice, timeout_ms=25_000)
        self._window.speak(prompt, hold_ms=25_000)

    def _on_launch_app_results_ready(self, apps: list[dict[str, Any]]) -> None:
        if self._window.is_closing:
            return
        if not apps:
            self._window.speak("Не удалось найти подходящих приложений.")
            return

        def _on_choice(text: str) -> str:
            choice = _parse_selected_number(text, max_number=len(apps))
            if choice is None:
                return "Не поняла номер. Запуск отменён."
            selected = apps[choice - 1]
            success = launch_application(selected)
            if success:
                return f"Запускаю #{choice}: {selected['name']}"
            return f"Не удалось запустить {selected['name']}."

        lines = [
            f"{i}. {a['name'][:32]}…" if len(a['name']) > 32 else f"{i}. {a['name']}"
            for i, a in enumerate(apps, 1)
        ]
        prompt = "\n".join(lines) + f"\nСкажи номер (1–{len(apps)})"
        self.flow.expect_reply(_on_choice, timeout_ms=25_000)
        self._window.speak(prompt, hold_ms=25_000)

    def _on_kill_app_results_ready(self, procs: list[dict[str, Any]]) -> None:
        if self._window.is_closing:
            return
        if not procs:
            self._window.speak("Не удалось найти подходящих процессов.")
            return

        def _on_choice(text: str) -> str:
            choice = _parse_selected_number(text, max_number=len(procs))
            if choice is None:
                return "Не поняла номер. Завершение отменено."
            selected = procs[choice - 1]
            success, count = kill_process_group(selected)
            name = selected["name"]
            if success:
                if count > 1:
                    return f"Завершено {count} процессов «{name}»."
                return f"Процесс «{name}» завершён."
            return f"Не удалось завершить {name}."

        lines = []
        for i, p in enumerate(procs, 1):
            name = p["name"]
            count = len(p.get("pids", []))
            count_label = f" ({count})" if count > 1 else ""
            display = f"{name}{count_label}"
            display = f"{display[:32]}…" if len(display) > 32 else display
            lines.append(f"{i}. {display}")

        prompt = "\n".join(lines) + f"\nСкажи номер (1–{len(procs)})"
        self.flow.expect_reply(_on_choice, timeout_ms=25_000)
        self._window.speak(prompt, hold_ms=25_000)

    def _on_update_check_finished(
        self, status: str, local_ver: Any, remote_ver: Any
    ) -> None:
        if self._window.is_closing:
            return
        if status == "update_available":
            def _on_confirm(text: str) -> str:
                from ..core.input_flow import AFFIRMATIVE_WORDS, _answer_words
                words = _answer_words(text)
                if words & AFFIRMATIVE_WORDS:
                    self.actions.open_update_page()
                    return "Открываю страницу обновлений на GitHub."
                return "Хорошо, пока не открываю."

            prompt = (
                f"Доступно обновление! ({local_ver} -> {remote_ver}). "
                "Открыть ссылку на GitHub? (да / нет)"
            )
            self.flow.expect_reply(_on_confirm, timeout_ms=20_000)
            self._window.speak(prompt, hold_ms=20_000)
