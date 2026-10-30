from __future__ import annotations

import getpass
import random
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import (
    QGuiApplication,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
    QScreen,
    QShortcut,
)
from PySide6.QtMultimedia import QAudioDevice, QMediaDevices
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QWidget

from ..audio.recognizer import get_model_info, is_model_ready, preload_model_async
from ..audio.voice import VoiceInput
from ..commands import CommandContext, register_default_commands
from ..controllers import ActionBridge, InactivityManager, PresenceReminder
from ..core.commands import CommandRegistry
from ..core.input_flow import InputFlow
from ..core.settings import (
    ACTIVITY_TIMEOUT_OPTIONS_MS,
    get_config_value,
    set_config_value,
)
from ..core.wake_word import (
    VOICE_COMMAND_WINDOW_MS,
    command_after_trigger,
)
from ..effects.glitch import GlitchManager
from ..effects.model_init_animation import ModelInitOverlay
from ..effects.session_animations import (
    SessionAnimationOverlay,
    play_session_animation,
)
from ..effects.transition import TransitionOverlay
from .context_menu import build_pet_context_menu, build_tray_context_menu
from .pet_renderer import PetRenderState, PetRenderer
from .speech import (
    SpeechWindow,
    close_all as close_all_speech,
    has_active_speech,
    show_text,
)
from .speech_sfx import get_speech_sfx

ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ROOT / "assets"
CAPRI_ICON = ASSETS / "capri_icon.png"
VAR_ASSETS = ASSETS / "var"
OVERLAY_SIT = VAR_ASSETS / "capri_sit.png"
OVERLAY_STAY = VAR_ASSETS / "capri_stay.png"
OVERLAY_CROUCH = VAR_ASSETS / "capri_crouch.png"

STARTUP_LINES = (
    "Хороший мальчик, {user}",
    "зови меня просто Капри!!!",
    "...",
)

GOODBYE_LINE = "пока пока чумба"

WAKE_LINES = (
    "Что?",
    "Слушаю.",
    "Я здесь.",
    "Да?",
    "Говори.",
)


class CapriWindow(QWidget):
    """Интерактивный питомец Капри."""

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setWindowTitle("Капри")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoFillBackground(False)

        self._scale_percent = 100
        self._volume_percent = 50
        self._raw_pixmaps: dict[str, QPixmap] = {}
        self._pixmaps: dict[str, QPixmap] = {}
        self._load_all_poses()
        self._current_pose = "sit"
        self._pixmap = self._pixmaps.get("sit") or next(iter(self._pixmaps.values()))
        self.setFixedSize(self._pixmap.size())

        self._drag_offset: QPoint | None = None
        self._speech: SpeechWindow | None = None
        self._greeted = False
        self._spawn_glitch_ticks = 24
        self._surge_ticks = 0
        self._pose_transition_ticks = 0
        self._is_dragging = False
        self._speaking = False
        self._anim_frame = 0
        self._telemetry_tag = "[CAPRI//ONLINE]"
        self._startup_overlay: TransitionOverlay | None = None
        self._model_init_overlay: ModelInitOverlay | None = None
        self._session_overlay: SessionAnimationOverlay | None = None
        self._voice_armed_until = 0.0
        self._closing = False
        self._designated_screen_name: str | None = None
        self._renderer = PetRenderer()
        self._started_at = time.monotonic()

        # Таймер анимации пиксельных глитчей
        self._glitch_timer = QTimer(self)
        self._glitch_timer.setInterval(70)
        self._glitch_timer.timeout.connect(self._on_glitch_tick)

        self.commands = CommandRegistry()
        self._flow = InputFlow(self.commands, self)
        self._actions = ActionBridge(self)
        self._actions.speech_requested.connect(self.speak)
        self._actions.session_animation_requested.connect(
            self._on_session_animation_requested
        )
        self._actions.ollama_started.connect(self._on_ollama_talking_start)
        self._actions.ollama_finished.connect(self._on_ollama_talking_end)
        self._actions.youtube_results_ready.connect(
            self._on_youtube_results_ready
        )

        self._build_shortcuts()
        self._glitches = GlitchManager(self)
        self._build_voice()
        self._load_initial_settings()
        self._register_commands()

        self._inactivity = InactivityManager(
            main_window=self,
            is_closing=lambda: self._closing,
            on_wake_voice=self._wake_voice_if_needed,
            get_designated_screen=self.get_designated_screen,
        )
        inactivity_ms = get_config_value(
            "behavior.inactivity_timeout_ms", ACTIVITY_TIMEOUT_OPTIONS_MS[0]
        )
        try:
            inactivity_ms = int(inactivity_ms)
        except (ValueError, TypeError):
            inactivity_ms = ACTIVITY_TIMEOUT_OPTIONS_MS[0]
        if inactivity_ms not in ACTIVITY_TIMEOUT_OPTIONS_MS:
            inactivity_ms = ACTIVITY_TIMEOUT_OPTIONS_MS[0]
        self._activity_timeout_seconds = inactivity_ms // 1000
        self._inactivity.set_timeout_ms(inactivity_ms)

        voice_enabled = get_config_value("audio.voice_enabled", True)
        if voice_enabled:
            self._voice.start()
        self._inactivity.start()

        self._reminder = PresenceReminder(self._on_reminder, self)
        self._reminders_enabled = bool(
            get_config_value("behavior.reminders_enabled", True)
        )
        if self._reminders_enabled:
            self._reminder.start()

        self._tray_icon: QSystemTrayIcon | None = None
        self._tray_menu = None
        self._init_tray()

    def _load_pixmap(self, name: str, path: Path) -> QPixmap:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            pixmap = QPixmap(420, 420)
        self._raw_pixmaps[name] = pixmap
        return self._apply_scale_for_pose(name)

    def _apply_scale_for_pose(self, name: str) -> QPixmap:
        raw = self._raw_pixmaps.get(name)
        if raw is None or raw.isNull():
            raw = QPixmap(420, 420)
            self._raw_pixmaps[name] = raw
        # 100% размер спрайта — базовый размер (width / 1.5, height / 1.5)
        base_width = max(1, int(raw.width() / 1.5))
        base_height = max(1, int(raw.height() / 1.5))
        scale_factor = self._scale_percent / 100.0
        target_width = max(1, int(base_width * scale_factor))
        target_height = max(1, int(base_height * scale_factor))
        scaled = raw.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._pixmaps[name] = scaled
        return scaled

    def set_sprite_scale(self, percent: int) -> None:
        if percent not in (50, 75, 100, 125, 150):
            return
        if self._scale_percent == percent:
            return
        self._scale_percent = percent
        set_config_value("appearance.scale", percent)
        for name in list(self._raw_pixmaps.keys()):
            self._apply_scale_for_pose(name)
        if self._current_pose in self._pixmaps:
            self._pixmap = self._pixmaps[self._current_pose]
            old_rect = self.geometry()
            self.setFixedSize(self._pixmap.size())
            # Центрируем изменение размера относительно текущей позиции
            new_x = old_rect.center().x() - self.width() // 2
            new_y = old_rect.bottom() - self.height()
            self.move(new_x, new_y)
            self.update()
            self.speak(f"Размер: {percent}%")

    def set_activity_timeout(self, seconds: int) -> None:
        """Задаёт время активности: через сколько секунд Капри исчезает с экрана."""
        timeout_ms = int(seconds) * 1000
        if timeout_ms not in ACTIVITY_TIMEOUT_OPTIONS_MS:
            return
        self._activity_timeout_seconds = timeout_ms // 1000
        set_config_value("behavior.inactivity_timeout_ms", timeout_ms)
        self._inactivity.set_timeout_ms(timeout_ms)
        self.speak(f"Время активности: {seconds} с")

    @property
    def activity_timeout_seconds(self) -> int:
        return self._activity_timeout_seconds

    def set_reminders_enabled(self, enabled: bool) -> None:
        """Включает или выключает случайные напоминания о себе."""
        enabled = bool(enabled)
        if self._reminders_enabled == enabled:
            return
        self._reminders_enabled = enabled
        set_config_value("behavior.reminders_enabled", enabled)
        if enabled:
            self._reminder.start()
            self.speak("Напоминания включены.")
        else:
            self._reminder.stop()
            self.speak("Напоминания выключены.")

    @property
    def reminders_enabled(self) -> bool:
        return self._reminders_enabled

    def _load_all_poses(self) -> None:
        pose_files = {
            "sit": OVERLAY_SIT,
            "stay": OVERLAY_STAY,
            "crouch": OVERLAY_CROUCH,
        }
        for pose_name, pose_path in pose_files.items():
            if pose_path.is_file():
                self._load_pixmap(pose_name, pose_path)
        if not self._pixmaps:
            fallback = QPixmap(420, 420)
            fallback.fill(Qt.GlobalColor.transparent)
            self._raw_pixmaps["sit"] = fallback
            self._apply_scale_for_pose("sit")

    def set_pose(self, pose: str) -> None:
        """Переключает спрайт позы питомца с эффектом цифровой киберпанк-реконструкции."""
        if pose not in self._pixmaps:
            pose_path = {
                "sit": OVERLAY_SIT,
                "stay": OVERLAY_STAY,
                "crouch": OVERLAY_CROUCH,
            }.get(pose)
            if pose_path is not None and pose_path.is_file():
                self._load_pixmap(pose, pose_path)
        if pose in self._pixmaps:
            old_pose = self._current_pose
            self._current_pose = pose
            self._pixmap = self._pixmaps[pose]
            self.setFixedSize(self._pixmap.size())
            if old_pose != pose:
                self._pose_transition_ticks = 6
                self._surge_ticks = max(self._surge_ticks, 6)
            self.update()

    def set_pose_image(self, pose_name: str, path: Path) -> None:
        """Переключает спрайт позы по пути к файлу."""
        self._load_pixmap(pose_name, path)
        self.set_pose(pose_name)

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Ctrl+Space"), self, self._toggle_voice)

    def _build_voice(self) -> None:
        if get_config_value("audio.voice_enabled", True):
            preload_model_async()
        self._voice = VoiceInput(always_on=False)
        self._voice.listening_changed.connect(self._on_voice_listening)
        self._voice.status_changed.connect(self._on_voice_status)
        self._voice.recognized.connect(self._on_voice_text)
        self._voice.failed.connect(self.speak)

        self._voice_window_timer = QTimer(self)
        self._voice_window_timer.setSingleShot(True)
        self._voice_window_timer.timeout.connect(self._on_voice_window_expired)

    def _register_commands(self) -> None:
        context = CommandContext(
            speak=self.speak,
            trigger_glitches=self._toggle_glitches,
            toggle_voice=self._toggle_voice,
            locate_mouse=self._locate_mouse,
            set_pose=self.set_pose,
            get_config=get_config_value,
            set_config=set_config_value,
            expect_reply=self._flow.expect_reply,
            action_bridge=self._actions,
            debug_info=self._debug_info,
        )
        self.commands.set_context(context)
        register_default_commands(self.commands)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        self._glitch_timer.start()
        if not self._greeted:
            self._greeted = True
            screen = (
                self.get_designated_screen()
                or self.screen()
                or QGuiApplication.primaryScreen()
            )
            if screen is not None:
                wh = self.windowHandle()
                if wh is not None:
                    wh.setScreen(screen)

                pos_data = get_config_value("window.position") or get_config_value("window.overlay_position")
                applied_pos = False
                if isinstance(pos_data, dict) and "x" in pos_data and "y" in pos_data:
                    target_rect = QRect(
                        int(pos_data["x"]),
                        int(pos_data["y"]),
                        self.width(),
                        self.height(),
                    )
                    if any(
                        s.availableGeometry().intersects(target_rect)
                        for s in QGuiApplication.screens()
                    ):
                        self.move(int(pos_data["x"]), int(pos_data["y"]))
                        applied_pos = True

                if not applied_pos:
                    geo = screen.availableGeometry()
                    cx = geo.left() + (geo.width() - self.width()) // 2
                    cy = geo.top() + (geo.height() - self.height()) // 2
                    self.move(cx, cy)

            screen_rect = (
                screen.geometry() if screen is not None else self.geometry()
            )
            self.set_pose("crouch")
            self._startup_overlay = TransitionOverlay(
                screen_rect,
                self.geometry(),
                "in",
                target=self,
                on_peak=self._reveal_on_startup,
            )
            self._startup_overlay.finished.connect(self._on_startup_finished)
            self._startup_overlay.start()

    def _reveal_on_startup(self) -> None:
        """Переход Капри из позы приземления в позу покоя на пике вспышки."""
        self.set_pose("sit")
        self.update()
        QTimer.singleShot(600, self._greet)

    def _on_startup_finished(self) -> None:
        self._startup_overlay = None
        self.set_pose("sit")
        self.update()
        self._start_model_init_animation()

    def _start_model_init_animation(self) -> None:
        """Показывает HUD инициализации Vosk, пока модель грузится в фоне."""
        if self._closing or self._model_init_overlay is not None:
            return
        if not get_config_value("audio.voice_enabled", True):
            return
        if is_model_ready():
            return
        screen = (
            self.get_designated_screen()
            or self.screen()
            or QGuiApplication.primaryScreen()
        )
        if screen is None:
            return
        info = get_model_info()
        overlay = ModelInitOverlay(
            screen.geometry(),
            str(info.get("model_name") or ""),
            parent=self,
        )
        overlay.finished.connect(self._forget_model_init)
        self._model_init_overlay = overlay
        overlay.start()

    def _forget_model_init(self) -> None:
        self._model_init_overlay = None

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._glitch_timer.stop()
        super().hideEvent(event)

    def _on_glitch_tick(self) -> None:
        self._anim_frame += 1
        if self._spawn_glitch_ticks > 0:
            self._spawn_glitch_ticks -= 1
        if self._surge_ticks > 0:
            self._surge_ticks -= 1
        if self._pose_transition_ticks > 0:
            self._pose_transition_ticks -= 1

        # Обновление киберпанк-телеметрии в нижнем индикаторе
        if self._anim_frame % 25 == 0:
            tags = (
                "[CAPRI//ONLINE]",
                "[HOLO//SYNC:OK]",
                "[SYS.LOAD: 42%]",
                "[NET//LINK:99%]",
                "[CORE: 3.8GHz]",
                "[BUS//TX:READY]",
                "[MEM:0xDEADBEEF]",
            )
            self._telemetry_tag = random.choice(tags)

        # Динамическая частота кадров глитча: высокая во время активности, экономная в простое
        if self._spawn_glitch_ticks > 0 or self._is_dragging or self._surge_ticks > 0:
            self._glitch_timer.setInterval(35)
        else:
            self._glitch_timer.setInterval(random.randint(65, 110))
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        state = PetRenderState(
            is_spawning=self._spawn_glitch_ticks > 0,
            is_dragging=self._is_dragging,
            is_pose_transition=self._pose_transition_ticks > 0,
            is_surge=self._surge_ticks > 0,
            is_speaking=self._speaking,
            telemetry_tag=self._telemetry_tag,
        )
        self._renderer.render(painter, self._pixmap, state)
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._inactivity.reset_timer()
        if event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._surge_ticks = max(self._surge_ticks, 10)
            self.update()
            try:
                get_speech_sfx().play_lightning_zap()
            except Exception:
                pass
            handle = self.windowHandle()
            if handle is not None and hasattr(handle, "startSystemMove"):
                handle.startSystemMove()
                event.accept()
                return
            self._drag_offset = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._drag_offset is not None or self._is_dragging:
            self._is_dragging = True
            self._surge_ticks = max(self._surge_ticks, 4)
            if self._drag_offset is not None:
                self.move(event.globalPosition().toPoint() - self._drag_offset)
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._is_dragging = False
        self._surge_ticks = max(self._surge_ticks, 6)
        if self._drag_offset is not None:
            pos = self.pos()
            set_config_value("window.position", {"x": pos.x(), "y": pos.y()})
            set_config_value("window.overlay_position", {"x": pos.x(), "y": pos.y()})
        self._drag_offset = None
        self.update()
        super().mouseReleaseEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and (
            self.isMaximized() or self.isFullScreen()
        ):
            QTimer.singleShot(0, self.showNormal)

    def process_input(self, text: str) -> str:
        return self._flow.handle(text)

    def speak(self, text: str, hold_ms: int | None = None) -> SpeechWindow:
        if self._speech is not None:
            self._speech.close(immediate=True)
        self._speaking = True
        self._surge_ticks = max(self._surge_ticks, 12)
        if hold_ms is None:
            hold_ms = min(5000, max(1200, len(text) * 45))
        speech = show_text(text, parent=self, hold_ms=hold_ms)
        self._speech = speech
        speech.destroyed.connect(
            lambda *_, window=speech: self._forget_speech(window)
        )
        return speech

    def _toggle_voice(self) -> str:
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

    def _on_voice_text(self, text: str) -> None:
        command = self._voice_command(text)
        if command is None:
            return
        self._inactivity.reset_timer()
        if command:
            self._disarm_voice_command()
            result = self.process_input(command)
            self.speak(result)
            return
        self._arm_voice_command()

    def _voice_command(self, text: str) -> str | None:
        command = command_after_trigger(text)
        if command is not None:
            return command
        if self._flow.awaiting_reply:
            return text.strip()
        if self._voice_command_armed:
            return text.strip()
        return None

    @property
    def _voice_command_armed(self) -> bool:
        return time.monotonic() < self._voice_armed_until

    def _arm_voice_command(self) -> None:
        self._voice_armed_until = (
            time.monotonic() + VOICE_COMMAND_WINDOW_MS / 1000
        )
        self._voice_window_timer.start(VOICE_COMMAND_WINDOW_MS)
        self._greet_trigger()

    def _disarm_voice_command(self) -> None:
        self._voice_armed_until = 0.0
        self._voice_window_timer.stop()

    def _on_voice_window_expired(self) -> None:
        self._voice_armed_until = 0.0

    def _greet_trigger(self) -> None:
        self.speak(random.choice(WAKE_LINES))

    def _wake_voice_if_needed(self) -> None:
        voice_enabled = get_config_value("audio.voice_enabled", True)
        if voice_enabled and not self._voice.is_listening and not self._voice.is_busy:
            self._voice.start()

    def _on_voice_listening(self, active: bool) -> None:
        pass

    def _on_voice_status(self, text: str) -> None:
        pass

    def _toggle_glitches(self) -> str:
        enabled = self._glitches.toggle()
        set_config_value("effects.glitches_enabled", enabled)
        return "Глитчи включены." if enabled else "Глитчи выключены."

    def _on_ollama_talking_start(self) -> None:
        self._surge_ticks = max(self._surge_ticks, 24)
        self.set_pose("stay")

    def _on_ollama_talking_end(self) -> None:
        self._surge_ticks = max(self._surge_ticks, 8)
        self.set_pose("sit")

    def _on_youtube_results_ready(self, videos: list[dict[str, str]]) -> None:
        if not videos or self._closing:
            return

        def _on_choice(text: str) -> str:
            from ..core.input_flow import _parse_selected_number
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
        self._flow.expect_reply(_on_choice, timeout_ms=25_000)
        self.speak(prompt, hold_ms=25_000)

    def _on_session_animation_requested(self, action: str) -> None:
        if self._closing:
            return
        if self._session_overlay is not None:
            try:
                self._session_overlay.close()
            except Exception:
                pass
            self._session_overlay = None

        overlay = play_session_animation(self, action)
        self._session_overlay = overlay
        overlay.finished.connect(
            lambda overlay=overlay: self._forget_session_animation(overlay)
        )

    def _forget_session_animation(self, overlay: SessionAnimationOverlay) -> None:
        if self._session_overlay is overlay:
            self._session_overlay = None

    def _locate_mouse(self) -> str:
        return self._inactivity.catch_mouse(
            on_pose_change=self.set_pose
        )

    def _debug_info(self) -> dict[str, object]:
        """Собирает диагностические данные для команды «дебаг»."""
        return {
            "vosk": get_model_info(),
            "next_reminder_seconds": self._reminder.seconds_until_next,
            "uptime_seconds": time.monotonic() - self._started_at,
        }

    def _load_initial_settings(self) -> None:
        screen_name = get_config_value("screen.designated_screen")
        self._designated_screen_name = None
        if screen_name:
            for scr in QGuiApplication.screens():
                if scr.name() == screen_name:
                    self._designated_screen_name = screen_name
                    break

        mic_desc = get_config_value("audio.designated_microphone")
        found_mic = False
        if mic_desc:
            for dev in QMediaDevices.audioInputs():
                if dev.description() == mic_desc:
                    self._voice.set_device(dev)
                    found_mic = True
                    break
        if not found_mic:
            self._voice.set_device(None)

        glitches_enabled = get_config_value("effects.glitches_enabled", True)
        self._glitches.set_enabled(bool(glitches_enabled))
        glitch_intensity = get_config_value("effects.glitch_intensity", "weak")
        self._glitches.set_intensity(str(glitch_intensity))

        speech_sfx = get_speech_sfx()
        volume_percent = get_config_value("audio.volume", 50)
        try:
            volume_val = int(volume_percent)
        except (ValueError, TypeError):
            volume_val = 50
        if volume_val not in (25, 50, 75, 100):
            volume_val = 50
        self._volume_percent = volume_val
        speech_sfx.set_volume(volume_val / 100.0)

        speech_sound = get_config_value("audio.speech_sound_enabled", True)
        speech_sfx.set_speech_sound_enabled(bool(speech_sound))

        effects_sound = get_config_value("audio.effects_sound_enabled", True)
        speech_sfx.set_effects_sound_enabled(bool(effects_sound))

        saved_scale = get_config_value("appearance.scale", 100)
        try:
            scale_val = int(saved_scale)
            if scale_val in (50, 75, 100, 125, 150):
                self._scale_percent = scale_val
                for name in list(self._raw_pixmaps.keys()):
                    self._apply_scale_for_pose(name)
        except (ValueError, TypeError):
            pass

        saved_pose = get_config_value("appearance.overlay_pose") or get_config_value("appearance.pose", "sit")
        self.set_pose(str(saved_pose))

    def get_designated_screen(self) -> QScreen | None:
        if self._designated_screen_name:
            for scr in QGuiApplication.screens():
                if scr.name() == self._designated_screen_name:
                    return scr
        return self.screen() or QGuiApplication.primaryScreen()

    def set_designated_screen(self, screen: QScreen) -> None:
        self._designated_screen_name = screen.name()
        set_config_value("screen.designated_screen", screen.name())

        geo = screen.availableGeometry()
        wh = self.windowHandle()
        if wh is not None:
            wh.setScreen(screen)

        cx = geo.left() + (geo.width() - self.width()) // 2
        cy = geo.top() + (geo.height() - self.height()) // 2
        self.move(cx, cy)
        set_config_value("window.position", {"x": cx, "y": cy})
        set_config_value("window.overlay_position", {"x": cx, "y": cy})
        self._inactivity.reset_timer()
        self.speak(f"Монитор: {screen.name()}")

    def set_designated_microphone(self, device: QAudioDevice | None) -> None:
        self._voice.set_device(device)
        desc = device.description() if device and not device.isNull() else ""
        set_config_value("audio.designated_microphone", desc if desc else None)
        name = desc if desc else "По умолчанию"
        self.speak(f"Микрофон: {name}")

    def set_speech_sound_enabled(self, enabled: bool) -> None:
        get_speech_sfx().set_speech_sound_enabled(enabled)
        set_config_value("audio.speech_sound_enabled", bool(enabled))
        status = "вкл" if enabled else "выкл"
        self.speak(f"Звук сообщений: {status}")

    def set_effects_sound_enabled(self, enabled: bool) -> None:
        get_speech_sfx().set_effects_sound_enabled(enabled)
        set_config_value("audio.effects_sound_enabled", bool(enabled))
        status = "вкл" if enabled else "выкл"
        self.speak(f"Звук эффектов: {status}")

    def set_master_volume(self, percent: int) -> None:
        if percent not in (25, 50, 75, 100):
            return
        if self._volume_percent == percent:
            return
        self._volume_percent = percent
        get_speech_sfx().set_volume(percent / 100.0)
        set_config_value("audio.volume", percent)
        self.speak(f"Громкость: {percent}%")

    @property
    def volume_percent(self) -> int:
        return self._volume_percent

    @property
    def scale_percent(self) -> int:
        return self._scale_percent

    @property
    def selected_microphone(self) -> QAudioDevice | None:
        return self._voice.selected_device

    @property
    def is_speaking(self) -> bool:
        return self._speaking or has_active_speech() or (self._speech is not None and self._speech.isVisible())

    @property
    def glitches_enabled(self) -> bool:
        return self._glitches.is_enabled

    @property
    def glitch_intensity(self) -> str:
        return self._glitches.intensity

    def set_glitch_intensity(self, intensity: str) -> None:
        self._glitches.set_intensity(intensity)
        set_config_value("effects.glitch_intensity", intensity)

    def toggle_voice(self) -> str:
        return self._toggle_voice()

    def show_context_menu(self, pos: QPoint) -> None:
        self._inactivity.set_paused(True)
        try:
            menu = build_pet_context_menu(self, pos)
            menu.exec(pos)
        finally:
            self._inactivity.set_paused(False)

    def _init_tray(self) -> None:
        icon = QIcon(str(CAPRI_ICON))
        if icon.isNull():
            pix = (
                self._pixmap
                if hasattr(self, "_pixmap") and not self._pixmap.isNull()
                else QPixmap(32, 32)
            )
            icon = QIcon(pix)

        self.setWindowIcon(icon)
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)

        self._tray_icon = QSystemTrayIcon(icon, self)
        self._tray_icon.setToolTip("CapriPet")

        self._tray_menu = build_tray_context_menu(self)
        self._tray_icon.setContextMenu(self._tray_menu)

        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _on_tray_activated(
        self, reason: QSystemTrayIcon.ActivationReason
    ) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.activate_command_mode()

    def activate_command_mode(self) -> None:
        """Показывает Капри и переводит в режим немедленного ожидания команды."""
        if self._closing:
            return

        if self._inactivity.is_transitioning:
            if self._inactivity._transition_overlay is not None:
                self._inactivity._transition_overlay.close()
                self._inactivity._transition_overlay = None
            self._inactivity._transitioning = False

        self.show()
        self.raise_()
        self.activateWindow()
        self._inactivity.reset_timer()

        self._wake_voice_if_needed()
        self._arm_voice_command()

    def _greet(self) -> None:
        if self._speech is not None:
            return
        if self._closing:
            return
        line = random.choice(STARTUP_LINES).format(user=getpass.getuser())
        self.speak(line)

    def _on_reminder(self, phrase: str) -> None:
        """Напоминает о себе: при необходимости возвращает Капри на экран и говорит фразу."""
        if self._closing or self._speaking or self._inactivity.is_paused:
            return
        if self.isVisible():
            self.speak(phrase)
            return
        self._inactivity.show_with_callback(lambda: self.speak(phrase))

    def _forget_speech(self, window: SpeechWindow) -> None:
        if self._speech is window:
            self._speech = None
            self._speaking = False
        if not self._closing and not self.is_speaking and hasattr(self, "_inactivity"):
            self._inactivity.reset_timer()

    def _finalize_quit(self) -> None:
        if getattr(self, "_exit_finalized", False):
            return
        self._exit_finalized = True
        if hasattr(self, "_exit_safety_timer") and self._exit_safety_timer is not None:
            self._exit_safety_timer.stop()
            self._exit_safety_timer = None
        if self._session_overlay is not None:
            try:
                self._session_overlay.close()
            except Exception:
                pass
            self._session_overlay = None
        if hasattr(self, "_exit_overlay") and self._exit_overlay is not None:
            try:
                self._exit_overlay.close()
            except Exception:
                pass
            self._exit_overlay = None
        if hasattr(self, "_tray_icon") and self._tray_icon is not None:
            self._tray_icon.hide()
        close_all_speech()
        self.hide()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._closing:
            event.accept()
            return

        try:
            pos = self.pos()
            set_config_value("window.position", {"x": pos.x(), "y": pos.y()})
            set_config_value("window.overlay_position", {"x": pos.x(), "y": pos.y()})
        except Exception:
            pass

        self._closing = True
        event.ignore()
        self._inactivity.stop()
        self._reminder.stop()
        if self._model_init_overlay is not None:
            try:
                self._model_init_overlay.close()
            except Exception:
                pass
            self._model_init_overlay = None
        self._glitch_timer.stop()
        self._voice_window_timer.stop()
        self._voice.cancel()
        self._glitches.stop()
        close_all_speech()

        speech = self.speak(GOODBYE_LINE)

        screen = self.screen() or QGuiApplication.primaryScreen()
        screen_rect = (
            screen.geometry() if screen is not None else self.geometry()
        )
        self._exit_overlay = TransitionOverlay(
            screen_rect, self.geometry(), "out", target=self
        )
        self._exit_overlay.start()

        self._exit_safety_timer = QTimer(self)
        self._exit_safety_timer.setSingleShot(True)
        self._exit_safety_timer.timeout.connect(self._finalize_quit)
        self._exit_safety_timer.start(2200)

        if speech is not None:
            speech.destroyed.connect(self._finalize_quit)
        else:
            self._exit_overlay.finished.connect(self._finalize_quit)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from main import main

    raise SystemExit(main())
