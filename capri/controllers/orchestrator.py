"""Оркестратор бизнес-логики CapriPet: связывает UI, аудио и команды."""

from __future__ import annotations

import contextlib
import random
import time
from typing import Any

from PySide6.QtCore import QObject, QPoint
from PySide6.QtGui import QGuiApplication

from ..audio.recognizer import get_model_info
from ..commands import CommandContext, register_default_commands
from ..commands.registry import CommandRegistry
from ..controllers.action_bridge import ActionBridge
from ..controllers.inactivity_manager import (
    InactivityManager,
    PresenceReminder,
)
from ..controllers.process_watcher import ProcessWatcher
from ..core.input_flow import (
    AFFIRMATIVE_WORDS,
    InputFlow,
    _parse_selected_number,
    answer_words,
)
from ..core.settings import (
    ACTIVITY_TIMEOUT_OPTIONS_MS,
    get_config_value,
    set_config_value,
)
from ..effects.session_animations import (
    SessionAnimationOverlay,
    play_session_animation,
)
from ..integrations.app_launcher import launch_application
from ..integrations.discord_rpc import DiscordRpcManager
from ..integrations.process_manager import kill_process_group
from ..integrations.system_volume import get_system_volume_service
from ..integrations.web_search import safe_open_url
from ..integrations.window_tracker import (
    get_active_window_rect,
    get_foreground_hwnd,
    shake_window_hwnd,
)
from ..ui.pet_renderer import pick_adjacent_position
from ..ui.speech_sfx import get_speech_sfx
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

        min_remind_ms = int(
            get_config_value("behavior.reminder_min_interval_ms", 600_000)
        )
        max_remind_ms = int(
            get_config_value(
                "behavior.reminder_max_interval_ms", 3_600_000
            )
        )
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

        discord_client_id = str(
            get_config_value("discord.client_id", "1567968896277938266")
        )
        self.discord_rpc = DiscordRpcManager(
            client_id=discord_client_id,
            track_provider=self.actions.spotify_current_track,
            parent=self,
        )
        self._discord_enabled = bool(
            get_config_value("discord.enabled", True)
        )
        self._last_command: str = "нет"
        self._sync_discord_status()

        self.process_watcher = ProcessWatcher(
            is_game_active=self._is_game_active,
            parent=self,
        )
        self.process_watcher.sig_process_context_changed.connect(
            self._on_process_context_changed
        )

        self._register_commands()

    def _connect_action_signals(self) -> None:
        self.actions.speech_requested.connect(self._window.speak)
        self.actions.session_animation_requested.connect(
            self._on_session_animation_requested
        )
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
            "behavior.inactivity_timeout_ms",
            ACTIVITY_TIMEOUT_OPTIONS_MS[0],
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
        self.process_watcher.start()
        if self._discord_enabled:
            self.discord_rpc.start()

    def stop(self) -> None:
        self.process_watcher.stop()
        self.discord_rpc.stop()
        self.inactivity.stop()
        self.reminder.stop()
        self.voice_coordinator.voice.cancel()
        if self._session_overlay is not None:
            with contextlib.suppress(Exception):
                self._session_overlay.close()
            self._session_overlay = None

    def pause(self) -> None:
        self.process_watcher.stop()
        self.inactivity.set_paused(True)
        self.reminder.stop()
        self.voice_coordinator.voice.cancel()

    def resume(self) -> None:
        self.inactivity.set_paused(False)
        self.process_watcher.start()
        self.voice_coordinator.wake_if_needed()

    def _is_game_active(self) -> bool:
        detector = getattr(self._window, "_game_detector", None)
        if detector and hasattr(detector, "is_game_active"):
            val = detector.is_game_active
            return bool(val() if callable(val) else val)
        return False

    def _on_process_context_changed(
        self, category: str, app_name: str, phrase: str
    ) -> None:
        """Реакция на смену рабочего контекста пользователя (ProcessWatcher)."""
        if getattr(self._window, "is_closing", False):
            return
        if getattr(self._window, "is_speaking", False):
            return

        # Если окно скрыто, показываем питомца перед воспроизведением реплики
        if not self._window.isVisible():
            self.inactivity.show_with_callback(lambda: self._window.speak(phrase))
        else:
            self._window.speak(phrase)

    @property
    def reminders_enabled(self) -> bool:
        return self._reminders_enabled

    @reminders_enabled.setter
    def reminders_enabled(self, val: bool) -> None:
        self._reminders_enabled = bool(val)

    def handle_command(self, text: str) -> None:
        self._last_command = text
        if self._discord_enabled:
            self._sync_discord_status()
        result = self.flow.handle(text)
        self._window.speak(result)

    def update_system_volume(
        self,
        delta: int | None = None,
        target: int | None = None,
        mute: bool | None = None,
        toggle_mute: bool = False,
    ) -> tuple[int, bool, float]:
        """Управление мастер-громкостью Windows с выводом OSD и звуком реле."""
        svc = get_system_volume_service()
        if toggle_mute:
            is_muted = svc.toggle_mute()
            vol = svc.get_volume()
        elif mute is not None:
            is_muted = svc.set_mute(mute)
            vol = svc.get_volume()
        elif target is not None:
            vol = svc.set_volume(target)
            is_muted = svc.is_muted()
        elif delta is not None:
            vol = svc.change_volume(delta)
            is_muted = svc.is_muted()
        else:
            vol = svc.get_volume()
            is_muted = svc.is_muted()

        vol_db = svc.get_volume_db()
        get_speech_sfx().play_relay_snap()

        show_hud = getattr(self._window, "show_volume_hud", None)
        if callable(show_hud):
            show_hud(vol, is_muted, vol_db)

        return vol, is_muted, vol_db

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
            open_console=getattr(self._window, "open_console", None),
            change_volume=self.update_system_volume,
        )
        self.commands.set_context(context)
        register_default_commands(self.commands)

    def set_discord_enabled(self, enabled: bool) -> None:
        self._discord_enabled = enabled
        set_config_value("discord.enabled", enabled)
        if enabled:
            self._sync_discord_status()
            self.discord_rpc.start()
        else:
            self.discord_rpc.stop()

    @property
    def process_monitoring_enabled(self) -> bool:
        """Статус работы контекстной телеметрии и мониторинга окон."""
        if hasattr(self, "process_watcher") and self.process_watcher is not None:
            return bool(self.process_watcher._enabled)
        return bool(get_config_value("telemetry.process_monitoring_enabled", True))

    def set_process_monitoring_enabled(self, enabled: bool) -> None:
        """Включает или выключает сенсорный конвейер отслеживания активных окон."""
        set_config_value("telemetry.process_monitoring_enabled", enabled)
        if hasattr(self, "process_watcher") and self.process_watcher is not None:
            self.process_watcher.set_enabled(enabled)

    def _sync_discord_status(self) -> None:
        last_cmd = self._last_command[:30] + (
            "…" if len(self._last_command) > 30 else ""
        )
        self.discord_rpc.update_presence(
            state="Модель: Vosk",
            details=f"Команда: {last_cmd}",
            large_text="CapriPet // Cyber AI",
        )

    def debug_info(self) -> dict[str, object]:
        return {
            "vosk": get_model_info(),
            "next_reminder_seconds": self.reminder.seconds_until_next,
            "uptime_seconds": time.monotonic() - self._started_at,
        }

    @property
    def window(self) -> Any:
        """Ссылка на главное окно питомца."""
        return self._window

    def _locate_mouse(self) -> str:
        self._window.teleport_controller.point_at_mouse()
        return "Вот курсор!"

    def trigger_reminder(self) -> None:
        phrase = self.reminder.next_phrase()
        self._on_reminder(phrase)

    def _on_reminder(self, phrase: str) -> None:
        if (
            self._window.is_closing
            or self._window.is_speaking
            or self.inactivity.is_paused
        ):
            return

        screen = self.inactivity.get_target_screen()
        target_hwnd = get_foreground_hwnd()
        target_rect = get_active_window_rect()
        effects = getattr(self._window, "effects", None)
        get_speech_sfx().play_core_destabilize()

        def _after_glitch_or_direct() -> None:
            if self._window.is_closing:
                return

            pet_w = self._window.width()
            pet_h = self._window.height()

            # Randomize destination point on screen or around active window
            if (
                target_rect is not None
                and target_rect.isValid()
                and random.random() < 0.6
            ):
                screen_area = (
                    screen.geometry()
                    if screen is not None
                    else target_rect
                )
                target_x, target_y, _ = pick_adjacent_position(
                    screen_area,
                    target_rect,
                    pet_w,
                    pet_h,
                    gap=24,
                )
            else:
                target_screen = (
                    screen
                    or self._window.screen()
                    or QGuiApplication.primaryScreen()
                )
                geo = (
                    target_screen.availableGeometry()
                    if target_screen is not None
                    else self._window.geometry()
                )
                max_x = max(geo.left(), geo.right() - pet_w)
                max_y = max(geo.top(), geo.bottom() - pet_h)
                target_x = random.randint(geo.left(), max_x)
                target_y = random.randint(geo.top(), max_y)

            target_pt = QPoint(
                target_x + pet_w // 2, target_y + pet_h // 2
            )

            def _on_appeared() -> None:
                self._window.speak(phrase)
                if hasattr(self._window, "prank_coordinator"):
                    self._window.prank_coordinator.on_pet_appeared()

            if self._window.isVisible():
                teleport_ctrl = getattr(self._window, "_teleport", None)
                if teleport_ctrl is not None:
                    teleport_ctrl.teleport_to_point(
                        target_pt,
                        mode="erratic_in",
                        on_finished_callback=_on_appeared,
                    )
                else:
                    self._window.move(target_x, target_y)
                    _on_appeared()
            else:
                self.inactivity.show_with_callback(
                    _on_appeared,
                    erratic=True,
                    target_pos=(target_x, target_y),
                )

        if target_hwnd is not None:
            shake_window_hwnd(
                target_hwnd, duration_ms=900, intensity=16, parent=self
            )

        if (
            effects is not None
            and target_rect is not None
            and target_rect.isValid()
        ):
            effects.glitch_burst(
                target_rect,
                duration_ms=950,
                intensity="extreme",
                on_finished=_after_glitch_or_direct,
            )
        else:
            _after_glitch_or_direct()

    def _on_session_animation_requested(self, action: str) -> None:
        if self._window.is_closing:
            return
        if self._session_overlay is not None:
            with contextlib.suppress(Exception):
                self._session_overlay.close()
            self._session_overlay = None

        overlay = play_session_animation(self._window, action)
        self._session_overlay = overlay
        overlay.finished.connect(
            lambda: self._forget_session_overlay(overlay)
        )

    def _forget_session_overlay(
        self, overlay: SessionAnimationOverlay
    ) -> None:
        if self._session_overlay is overlay:
            self._session_overlay = None

    def _on_youtube_results_ready(
        self, videos: list[dict[str, str]]
    ) -> None:
        if not videos or self._window.is_closing:
            return

        def _on_choice(text: str) -> str:
            choice = _parse_selected_number(text, max_number=len(videos))
            if choice is None:
                return "Чё ты там пробормотал? Цифру не разобрала. Отбой!"
            selected = videos[choice - 1]
            safe_open_url(selected["url"])
            return f"Врубаю #{choice}: {selected['title']}! Погнали!"

        lines = [
            f"{i}. {v['title'][:32]}…"
            if len(v["title"]) > 32
            else f"{i}. {v['title']}"
            for i, v in enumerate(videos, 1)
        ]
        prompt = "\n".join(lines) + "\nКакое видео крутить? Назови номер (1–5)!"
        self.flow.expect_reply(_on_choice, timeout_ms=25_000)
        self._window.speak(prompt, hold_ms=25_000)

    def _on_launch_app_results_ready(
        self, apps: list[dict[str, Any]]
    ) -> None:
        if self._window.is_closing:
            return
        if not apps:
            self._window.speak("Отказ! В твоих каталогах нет ничего похожего. Ты точно не опечатался?")
            return

        def _on_choice(text: str) -> str:
            choice = _parse_selected_number(text, max_number=len(apps))
            if choice is None:
                return "Не разобрала номер. Отменяю запуск!"
            selected = apps[choice - 1]
            success = launch_application(selected)
            if success:
                return f"Врубаю на полную #{choice}: {selected['name']}!"
            return f"Чёрт, эта софтина ({selected['name']}) не хочет стартовать! Разбирайся сам."

        lines = [
            f"{i}. {a['name'][:32]}…"
            if len(a["name"]) > 32
            else f"{i}. {a['name']}"
            for i, a in enumerate(apps, 1)
        ]
        prompt = "\n".join(lines) + f"\nКакую софтину запускаем? Назови номер (1–{len(apps)})!"
        self.flow.expect_reply(_on_choice, timeout_ms=25_000)
        self._window.speak(prompt, hold_ms=25_000)

    def _on_kill_app_results_ready(
        self, procs: list[dict[str, Any]]
    ) -> None:
        if self._window.is_closing:
            return
        if not procs:
            self._window.speak("Ни одного такого процесса в памяти нет. Кого глушить-то собрался, призраков?")
            return

        def _on_choice(text: str) -> str:
            choice = _parse_selected_number(text, max_number=len(procs))
            if choice is None:
                return "Не разобрала номер. Отбой охоты на процессы!"
            selected = procs[choice - 1]
            success, count = kill_process_group(selected)
            name = selected["name"]
            if success:
                if count > 1:
                    return f"Выкосила пачку из {count} процессов «{name}»! В стеке чисто."
                return f"«{name}» ликвидирован! Ледоруб сработал чисто, память свободна."
            return f"Чёрт, не вышло прибить {name}. Он засел намертво!"

        lines = []
        for i, p in enumerate(procs, 1):
            name = p["name"]
            count = len(p.get("pids", []))
            count_label = f" ({count})" if count > 1 else ""
            display = f"{name}{count_label}"
            display = f"{display[:32]}…" if len(display) > 32 else display
            lines.append(f"{i}. {display}")

        prompt = "\n".join(lines) + f"\nКто тут лишний жрёт память? Назови номер цели (1–{len(procs)})!"
        self.flow.expect_reply(_on_choice, timeout_ms=25_000)
        self._window.speak(prompt, hold_ms=25_000)

    def _on_update_check_finished(
        self, status: str, local_ver: Any, remote_ver: Any
    ) -> None:
        if self._window.is_closing:
            return
        if status == "update_available":

            def _on_confirm(text: str) -> str:
                words = answer_words(text)
                if words & AFFIRMATIVE_WORDS:
                    self.actions.open_update_page()
                    return "Открываю страницу на GitHub. Качаем апгрейд!"
                return "Ладно, сидим на старой версии."

            prompt = (
                f"Опа, создатели выкатили для меня апгрейд! ({local_ver} -> {remote_ver}). "
                "Лезем на GitHub за свежим кодом? (да / нет)"
            )
            self.flow.expect_reply(_on_confirm, timeout_ms=20_000)
            self._window.speak(prompt, hold_ms=20_000)
