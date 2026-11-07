"""Главное окно настольного кибер-питомца Capri.

Управляет жизненным циклом прозрачного оверлейного окна питомца,
обработкой пользовательского ввода, анимациями и интеграциями подсистем.
"""

from __future__ import annotations

import contextlib
import getpass
import random
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import (
    QGuiApplication,
    QKeySequence,
    QPainter,
    QPixmap,
    QScreen,
    QShortcut,
)
from PySide6.QtMultimedia import QAudioDevice, QMediaDevices
from PySide6.QtWidgets import QApplication, QWidget

from ..audio.recognizer import (
    get_model_info,
    is_model_ready,
    preload_model_async,
)
from ..controllers.orchestrator import PetOrchestrator
from ..core.settings import (
    ACTIVITY_TIMEOUT_OPTIONS_MS,
    get_config_value,
    set_config_value,
)
from ..effects.effects_coordinator import EffectsCoordinator
from ..effects.model_init_animation import ModelInitOverlay
from ..effects.session_animations import SessionAnimationOverlay
from ..effects.transition import TransitionOverlay
from ..integrations.game_mode import GameModeDetector
from ..integrations.system_power_hook import SystemEventHook
from .context_menu import TrayManager, build_pet_context_menu
from .game_overlay import SilentPresenceGlyph
from .pet_renderer import PetRenderer, PetRenderState
from .speech import (
    SpeechWindow,
    has_active_speech,
    set_speech_suppressed,
)
from .speech import (
    close_all as close_all_speech,
)
from .speech_sfx import get_speech_sfx
from .sprite_manager import SpriteManager
from .teleport_controller import TeleportController

ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ROOT / "assets"
CAPRI_ICON = ASSETS / "capri_icon.png"
VAR_ASSETS = ASSETS / "var"

IDLE_DIR = VAR_ASSETS / "idle"
OTHER_DIR = VAR_ASSETS / "other"
THINKING_DIR = VAR_ASSETS / "thinking"

OVERLAY_IDLE = IDLE_DIR / "1.png"
OVERLAY_OTHER = OTHER_DIR / "1.png"
OVERLAY_THINKING = THINKING_DIR / "1.png"

OVERLAY_SIT = OVERLAY_IDLE
OVERLAY_STAY = OVERLAY_THINKING
OVERLAY_CROUCH = OVERLAY_OTHER

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
    """Основное прозрачное окно рабочего стола с интерактивным питомцем."""

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

        self._volume_percent = 50
        self._sprite_manager = SpriteManager(self._on_sprite_changed)
        self.setFixedSize(self._sprite_manager.current_pixmap.size())

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
        self._closing = False
        self._designated_screen_name: str | None = None
        self._renderer = PetRenderer()
        self._started_at = time.monotonic()

        self._teleport = TeleportController(self)

        self._glitch_timer = QTimer(self)
        self._glitch_timer.setInterval(70)
        self._glitch_timer.timeout.connect(self._on_glitch_tick)

        self._effects = EffectsCoordinator(self)
        self._orchestrator = PetOrchestrator(self)
        self._build_shortcuts()
        self._load_initial_settings()

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
        self._activity_timeout_seconds = inactivity_ms // 1000

        self._power_hook = SystemEventHook(
            on_suspend=self._on_system_suspend,
            on_shutdown=self._on_system_shutdown,
            on_lock=self._on_session_lock,
            on_unlock=self._on_session_unlock,
        )

        self._orchestrator.start()
        self._tray = TrayManager(self)
        self._silent_glyph = SilentPresenceGlyph()
        self._is_stealth_mode = False
        self._stealth_origin_pos: QPoint | None = None
        self._stealth_transition_overlay: TransitionOverlay | None = None

        game_suppression = bool(
            get_config_value("game_mode.suppression_enabled", True)
        )
        game_cooldown = float(
            get_config_value("game_mode.cooldown_seconds", 3.0)
        )
        game_whitelist = list(get_config_value("game_mode.whitelist", []))
        game_blacklist = list(get_config_value("game_mode.blacklist", []))
        self._game_detector = GameModeDetector(
            suppression_enabled=game_suppression,
            cooldown_seconds=game_cooldown,
            whitelist=game_whitelist,
            blacklist=game_blacklist,
            parent=self,
        )
        self._game_detector.game_mode_changed.connect(
            self._on_game_mode_changed
        )

    @property
    def orchestrator(self) -> PetOrchestrator:
        return self._orchestrator

    @property
    def teleport_controller(self) -> TeleportController:
        return self._teleport

    @property
    def commands(self):
        return self._orchestrator.commands

    @property
    def input_flow(self):
        return self._orchestrator.flow

    @property
    def inactivity_manager(self):
        return self._orchestrator.inactivity

    @property
    def voice_coordinator(self):
        return self._orchestrator.voice_coordinator

    @property
    def is_closing(self) -> bool:
        return self._closing

    @property
    def surge_ticks(self) -> int:
        return self._surge_ticks

    @surge_ticks.setter
    def surge_ticks(self, val: int) -> None:
        self._surge_ticks = val

    @property
    def pixmap(self) -> QPixmap:
        return self._sprite_manager.current_pixmap

    def _on_sprite_changed(
        self, pixmap: QPixmap, hit_image, pose_name: str
    ) -> None:
        old_size = self.size()
        self.setFixedSize(pixmap.size())
        if old_size != pixmap.size() and old_size.isValid():
            old_rect = self.geometry()
            new_x = old_rect.center().x() - self.width() // 2
            new_y = old_rect.bottom() - self.height()
            self.move(new_x, new_y)
        mask_region = self._sprite_manager.cached_mask_region
        if mask_region is not None and not mask_region.isEmpty():
            self.setMask(mask_region)
        else:
            self.clearMask()
        self.update()

    def set_sprite_scale(self, percent: int) -> None:
        if self._sprite_manager.set_sprite_scale(percent):
            self.speak(f"Размер: {percent}%")

    def set_activity_timeout(self, seconds: int) -> None:

        timeout_ms = int(seconds) * 1000
        if timeout_ms not in ACTIVITY_TIMEOUT_OPTIONS_MS:
            return
        self._activity_timeout_seconds = timeout_ms // 1000
        set_config_value("behavior.inactivity_timeout_ms", timeout_ms)
        self._orchestrator.inactivity.set_timeout_ms(timeout_ms)
        self.speak(f"Время активности: {seconds} с")

    @property
    def activity_timeout_seconds(self) -> int:
        return self._activity_timeout_seconds

    def set_reminders_enabled(self, enabled: bool) -> None:

        enabled = bool(enabled)
        if self._orchestrator._reminders_enabled == enabled:
            return
        self._orchestrator._reminders_enabled = enabled
        set_config_value("behavior.reminders_enabled", enabled)
        if enabled:
            self._orchestrator.reminder.start()
            self.speak("Напоминания включены.")
        else:
            self._orchestrator.reminder.stop()
            self.speak("Напоминания выключены.")

    @property
    def reminders_enabled(self) -> bool:
        return self._orchestrator._reminders_enabled

    def set_reminder_interval_range(
        self, min_ms: int, max_ms: int
    ) -> None:

        self._orchestrator.reminder.set_interval_range(min_ms, max_ms)
        set_config_value(
            "behavior.reminder_min_interval_ms",
            self._orchestrator.reminder.min_interval_ms,
        )
        set_config_value(
            "behavior.reminder_max_interval_ms",
            self._orchestrator.reminder.max_interval_ms,
        )

    @property
    def reminder_interval_range(self) -> tuple[int, int]:
        return (
            self._orchestrator.reminder.min_interval_ms,
            self._orchestrator.reminder.max_interval_ms,
        )

    def set_pose(self, pose: str) -> None:

        changed = self._sprite_manager.set_pose(pose)
        if changed:
            self._pose_transition_ticks = 6
            self._surge_ticks = max(self._surge_ticks, 6)

    def set_pose_image(self, pose_name: str, path: Path) -> None:

        self._sprite_manager.set_pose_image(pose_name, path)

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(
            QKeySequence("Ctrl+Space"),
            self,
            self._orchestrator.voice_coordinator.toggle_voice,
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._glitch_timer.start()
        try:
            hwnd = int(self.winId())
            self._power_hook.register_session_notification(hwnd)
        except Exception:
            pass
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

                pos_data = get_config_value(
                    "window.position"
                ) or get_config_value("window.overlay_position")
                applied_pos = False
                if (
                    isinstance(pos_data, dict)
                    and "x" in pos_data
                    and "y" in pos_data
                ):
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
                screen.geometry()
                if screen is not None
                else self.geometry()
            )
            self.set_pose("idle")
            self.hide()
            self._startup_overlay = TransitionOverlay(
                screen_rect,
                self.geometry(),
                "in",
                target=self,
                on_peak=self._reveal_on_startup,
            )
            self._startup_overlay.finished.connect(
                self._on_startup_finished
            )
            self._startup_overlay.start()

    def _reveal_on_startup(self) -> None:
        self.set_pose("idle")
        self.show()
        self.raise_()
        self.update()
        QTimer.singleShot(600, self._greet)

    def _on_startup_finished(self) -> None:
        self._startup_overlay = None
        self.set_pose("idle")
        self.show()
        self.raise_()
        self.update()
        self._start_model_init_animation()

    def _start_model_init_animation(self) -> None:

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

    def hideEvent(self, event) -> None:
        if self._teleport.is_aiming:
            self._teleport.cancel_aiming()
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

        if (
            self._spawn_glitch_ticks > 0
            or self._is_dragging
            or self._surge_ticks > 0
        ):
            self._glitch_timer.setInterval(35)
        else:
            self._glitch_timer.setInterval(random.randint(65, 110))
        self.update()

    def paintEvent(self, _event) -> None:
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
        self._renderer.render(painter, self.pixmap, state)
        painter.end()

    def _is_point_on_sprite(self, pos: QPoint) -> bool:

        return self._sprite_manager.is_point_on_sprite(pos.x(), pos.y())

    def mousePressEvent(self, event) -> None:
        pos = event.position().toPoint()
        if not self._is_point_on_sprite(pos):
            event.ignore()
            return

        self._orchestrator.inactivity.reset_timer()
        if event.button() == Qt.MouseButton.RightButton:
            if self._teleport.is_aiming:
                self._teleport.cancel_aiming()
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return

        if self._teleport.handle_mouse_press(event):
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._teleport.handle_mouse_move(event):
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._teleport.handle_mouse_release(event):
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and (
            self.isMaximized() or self.isFullScreen()
        ):
            QTimer.singleShot(0, self.showNormal)

    def toggle_glitches(self) -> str:
        return self._toggle_glitches()

    def process_input(self, text: str) -> str:
        return self._orchestrator.flow.handle(text)

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
                    self._orchestrator.voice_coordinator.set_device(dev)
                    found_mic = True
                    break
        if not found_mic:
            self._orchestrator.voice_coordinator.set_device(None)

        glitches_enabled = get_config_value(
            "effects.glitches_enabled", True
        )
        self._effects.glitches.set_enabled(bool(glitches_enabled))
        glitch_intensity = get_config_value(
            "effects.glitch_intensity", "weak"
        )
        self._effects.set_glitch_intensity(str(glitch_intensity))

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

        effects_sound = get_config_value(
            "audio.effects_sound_enabled", True
        )
        speech_sfx.set_effects_sound_enabled(bool(effects_sound))

        saved_pose = get_config_value(
            "appearance.overlay_pose"
        ) or get_config_value("appearance.pose", "sit")
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
        self._orchestrator.inactivity.reset_timer()
        self.speak(f"Монитор: {screen.name()}")

    def set_designated_microphone(
        self, device: QAudioDevice | None
    ) -> None:
        self._orchestrator.voice_coordinator.set_device(device)
        desc = (
            device.description() if device and not device.isNull() else ""
        )
        set_config_value(
            "audio.designated_microphone", desc if desc else None
        )
        name = desc if desc else "По умолчанию"
        self.speak(f"Микрофон: {name}")

    def set_asr_backend(self, backend: str) -> None:
        from ..audio.recognizer import set_backend

        set_backend(backend)
        preload_model_async()
        label = "Faster-Whisper" if backend == "whisper" else "Vosk"
        self._orchestrator.update_discord_asr(backend)
        self.speak(f"Модель речи: {label}")

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
        return self._sprite_manager.scale_percent

    @property
    def selected_microphone(self) -> QAudioDevice | None:
        return self._orchestrator.voice_coordinator.selected_device

    @property
    def is_speaking(self) -> bool:
        return (
            self._speaking
            or has_active_speech()
            or (self._speech is not None and self._speech.isVisible())
        )

    @property
    def effects(self) -> EffectsCoordinator:
        return self._effects

    @property
    def glitches_enabled(self) -> bool:
        return self._effects.is_glitch_enabled

    @property
    def glitch_intensity(self) -> str:
        return self._effects.glitch_intensity

    def set_glitch_intensity(self, intensity: str) -> None:
        self._effects.set_glitch_intensity(intensity)
        set_config_value("effects.glitch_intensity", intensity)

    def _toggle_glitches(self) -> str:
        enabled = self._effects.toggle_glitches()
        set_config_value("effects.glitches_enabled", enabled)
        return "Глитчи включены." if enabled else "Глитчи выключены."

    def toggle_voice(self) -> str:
        return self._orchestrator.voice_coordinator.toggle_voice()

    def set_discord_enabled(self, enabled: bool) -> None:
        self._orchestrator.set_discord_enabled(enabled)
        status = "вкл" if enabled else "выкл"
        self.speak(f"Discord RPC: {status}")

    def show_context_menu(self, pos: QPoint) -> None:
        self._orchestrator.inactivity.set_paused(True)
        try:
            menu = build_pet_context_menu(self, pos)
            menu.exec(pos)
        finally:
            self._orchestrator.inactivity.set_paused(False)

    def activate_command_mode(self) -> None:

        if self._closing:
            return

        if self._orchestrator.inactivity.is_transitioning:
            if (
                self._orchestrator.inactivity._transition_overlay
                is not None
            ):
                self._orchestrator.inactivity._transition_overlay.close()
                self._orchestrator.inactivity._transition_overlay = None
            self._orchestrator.inactivity._transitioning = False

        self.show()
        self.raise_()
        self.activateWindow()
        self._orchestrator.inactivity.reset_timer()

        self._orchestrator.voice_coordinator.wake_if_needed()
        self._orchestrator.voice_coordinator._arm()

    def _greet(self) -> None:
        if self._speech is not None:
            return
        if self._closing:
            return
        line = random.choice(STARTUP_LINES).format(user=getpass.getuser())
        self.speak(line)

    def _forget_speech(self, window: SpeechWindow) -> None:
        try:
            if not self.isVisible() and not self.isHidden():
                return
        except RuntimeError:
            return
        if self._speech is window:
            self._speech = None
            self._speaking = False
        if (
            not self._closing
            and not self.is_speaking
            and hasattr(self, "_orchestrator")
        ):
            self._orchestrator.inactivity.reset_timer()

    def _finalize_quit(self) -> None:
        if getattr(self, "_exit_finalized", False):
            return
        self._exit_finalized = True
        if (
            hasattr(self, "_exit_safety_timer")
            and self._exit_safety_timer is not None
        ):
            self._exit_safety_timer.stop()
            self._exit_safety_timer = None
        if self._session_overlay is not None:
            with contextlib.suppress(Exception):
                self._session_overlay.close()
            self._session_overlay = None
        if (
            hasattr(self, "_exit_overlay")
            and self._exit_overlay is not None
        ):
            with contextlib.suppress(Exception):
                self._exit_overlay.close()
            self._exit_overlay = None
        if hasattr(self, "_tray_icon") and self._tray_icon is not None:
            self._tray_icon.hide()
        if hasattr(self, "_power_hook") and self._power_hook is not None:
            self._power_hook.unregister_session_notification()
        close_all_speech()
        self.hide()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def closeEvent(self, event) -> None:
        if self._closing:
            event.accept()
            return

        try:
            pos = self.pos()
            set_config_value(
                "window.position", {"x": pos.x(), "y": pos.y()}
            )
            set_config_value(
                "window.overlay_position", {"x": pos.x(), "y": pos.y()}
            )
        except Exception:
            pass

        self._closing = True
        event.ignore()
        self._orchestrator.stop()
        self._effects.stop_all()
        self._glitch_timer.stop()
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

    def _on_system_suspend(self) -> None:
        self._fast_terminate()

    def _on_system_shutdown(self) -> None:
        self._fast_terminate()

    def _on_session_lock(self) -> None:
        if self._closing:
            return
        self._orchestrator.pause()
        self._glitch_timer.stop()

    def _on_session_unlock(self) -> None:
        if self._closing:
            return
        self._glitch_timer.start()
        self._orchestrator.resume()
        self.trigger_pose_transition()

    def _fast_terminate(self) -> None:
        if self._closing:
            return
        self._closing = True
        try:
            pos = self.pos()
            set_config_value(
                "window.position", {"x": pos.x(), "y": pos.y()}
            )
            set_config_value(
                "window.overlay_position", {"x": pos.x(), "y": pos.y()}
            )
        except Exception:
            pass
        self._orchestrator.stop()
        self._effects.stop_all()
        self._glitch_timer.stop()
        self._finalize_quit()

    def _on_game_mode_changed(self, active: bool) -> None:
        self._is_stealth_mode = active
        set_speech_suppressed(active)
        get_speech_sfx().set_suppressed(active)
        if hasattr(self._orchestrator, "reminder"):
            self._orchestrator.reminder.set_suppressed(active)

        if self._stealth_transition_overlay is not None:
            try:
                self._stealth_transition_overlay.stop()
                self._stealth_transition_overlay.deleteLater()
            except Exception:
                pass
            self._stealth_transition_overlay = None

        screen = (
            self.get_designated_screen() or QGuiApplication.primaryScreen()
        )
        screen_rect = screen.geometry() if screen else self.geometry()
        glyph_center = self._silent_glyph.geometry().center()

        if active:
            if not self.isVisible():
                self._silent_glyph.show()
                return

            self._stealth_origin_pos = self.pos()
            overlay = TransitionOverlay(
                screen_rect,
                self.geometry(),
                "stealth_enter",
                target=self,
                target_point=glyph_center,
            )
            self.hide()

            def on_stealth_in_finish():
                self._stealth_transition_overlay = None
                self._silent_glyph.show()

            overlay.finished.connect(on_stealth_in_finish)
            self._stealth_transition_overlay = overlay
            overlay.start()
        else:
            self._silent_glyph.hide()
            if self._closing:
                return

            if self._stealth_origin_pos is not None:
                orig_x = self._stealth_origin_pos.x()
                orig_y = self._stealth_origin_pos.y()
                self.move(orig_x, orig_y)
            else:
                center_x = screen_rect.center().x() - self.width() // 2
                center_y = screen_rect.center().y() - self.height() // 2
                self.move(center_x, center_y)

            overlay = TransitionOverlay(
                screen_rect,
                self.geometry(),
                "stealth_exit",
                target=self,
                target_point=glyph_center,
                on_peak=self._reveal_on_stealth_peak,
            )

            def on_stealth_out_finish():
                self._stealth_transition_overlay = None

            overlay.finished.connect(on_stealth_out_finish)
            self._stealth_transition_overlay = overlay
            overlay.start()

    def _reveal_on_stealth_peak(self) -> None:
        if not self._closing and not self._is_stealth_mode:
            self.show()
            self.raise_()

    def set_game_suppression_enabled(self, enabled: bool) -> None:
        set_config_value("game_mode.suppression_enabled", enabled)
        self._game_detector.set_enabled(enabled)

    @property
    def game_suppression_enabled(self) -> bool:
        return self._game_detector.suppression_enabled

    def nativeEvent(
        self, event_type: bytes | bytearray, message: int | object
    ) -> tuple[bool, int]:
        if event_type in (
            b"windows_generic_MSG",
            b"windows_dispatcher_MSG",
        ):
            try:
                from ctypes import wintypes

                msg = wintypes.MSG.from_address(int(message))
                if self._power_hook.handle_windows_message(
                    msg.message, msg.wParam, msg.lParam
                ):
                    return True, 0
            except Exception:
                pass
        return super().nativeEvent(event_type, message)
