from __future__ import annotations

import getpass
import random
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QActionGroup, QGuiApplication, QKeySequence, QScreen, QShortcut
from PySide6.QtMultimedia import QAudioDevice, QMediaDevices
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from ..audio.voice import VoiceInput
from ..controllers import ActionBridge, InactivityManager, MediaController, PHASE_CLOSED
from ..core.command_catalog import Handlers, register_commands
from ..core.commands import CommandRegistry
from ..core.input_flow import InputFlow
from ..core.settings import get_config_value, set_config_value
from ..core.wake_word import (
    VOICE_COMMAND_WINDOW_MS,
    command_after_trigger,
)
from ..effects.glitch import GlitchManager
from ..effects.transition import TransitionOverlay
from .overlay_window import CapriOverlayWindow
from .speech import SpeechWindow, close_all as close_all_speech, show_text
from .speech_sfx import get_speech_sfx
from .theme import APP_STYLE

ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ROOT / "assets"
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


class CapriWindow(QWidget):
    """Главное окно интерактивного питомца Капри."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CAPRI")
        self.setFixedSize(800, 540)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setStyleSheet(APP_STYLE)

        self._drag_offset: QPoint | None = None
        self._speech: SpeechWindow | None = None
        self._greeted = False
        self._voice_armed_until = 0.0
        self._closing = False
        self._default_status = "Капри // Слушает"
        self._overlay_mode = False
        self._overlay_window: CapriOverlayWindow | None = None
        self._designated_screen_name: str | None = None

        self.commands = CommandRegistry()
        self._flow = InputFlow(self.commands, self)
        self._actions = ActionBridge(self)
        self._actions.speech_requested.connect(self.speak)
        self._actions.ollama_started.connect(self._on_ollama_talking_start)
        self._actions.ollama_finished.connect(self._on_ollama_talking_end)

        self._build_ui()
        self._media = MediaController(self, self.video)
        self._media.error_occurred.connect(self._on_media_error)
        self._media.outro_completed.connect(self._finish_close)

        self._build_shortcuts()
        self._glitches = GlitchManager(self)
        self._build_voice()
        self._load_initial_settings()
        self._register_commands()

        self._inactivity = InactivityManager(
            main_window=self,
            get_overlay=lambda: self._overlay_window,
            is_overlay_mode=lambda: self._overlay_mode,
            is_closing=lambda: self._closing or self._media.phase == PHASE_CLOSED,
            on_wake_voice=self._wake_voice_if_needed,
            get_designated_screen=self.get_designated_screen,
        )
        inactivity_ms = get_config_value("behavior.inactivity_timeout_ms", 5000)
        self._inactivity.set_timeout_ms(int(inactivity_ms))

        self._media.start_playback()
        voice_enabled = get_config_value("audio.voice_enabled", True)
        if voice_enabled:
            self._voice.start()
        self._inactivity.start()

    def _build_ui(self) -> None:
        self.video = QVideoWidget(self)
        self.video.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.video.setMinimumSize(320, 180)

        panel = QWidget(self)
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 12, 16, 14)
        panel_layout.setSpacing(8)

        self.status = QLabel(self._default_status, panel)
        self.status.setObjectName("status")
        panel_layout.addWidget(self.status)

        accent = QFrame(self)
        accent.setObjectName("accent")
        accent.setFixedHeight(3)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.video, 1)
        layout.addWidget(accent)
        layout.addWidget(panel)

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Ctrl+Space"), self, self._toggle_voice)

    def _build_voice(self) -> None:
        self._voice = VoiceInput(always_on=False)
        self._voice.listening_changed.connect(self._on_voice_listening)
        self._voice.status_changed.connect(self._on_voice_status)
        self._voice.recognized.connect(self._on_voice_text)
        self._voice.failed.connect(self.speak)

        self._voice_window_timer = QTimer(self)
        self._voice_window_timer.setSingleShot(True)
        self._voice_window_timer.timeout.connect(self._on_voice_window_expired)

    def _register_commands(self) -> None:
        register_commands(
            self.commands,
            Handlers(
                toggle_glitches=self._toggle_glitches,
                toggle_voice=self._toggle_voice,
                wild_glitch=self._wild_glitch,
                ask_ollama=self._actions.ask_ollama,
                search_google=self._actions.search_google,
                search_youtube=self._actions.search_youtube,
                spotify_play=self._actions.spotify_play,
                spotify_pause=self._actions.spotify_pause,
                spotify_resume=self._actions.spotify_resume,
                spotify_next=self._actions.spotify_next,
                spotify_previous=self._actions.spotify_previous,
                lock_screen=self._actions.lock_screen,
                power_off=self._actions.power_off,
                suspend=self._actions.suspend,
                reboot=self._actions.reboot,
                toggle_overlay=self._toggle_capri_overlay,
                locate_mouse=self._locate_mouse,
            ),
        )

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        if not self._greeted:
            self._greeted = True
            screen = self.get_designated_screen() or self.screen() or QGuiApplication.primaryScreen()
            if screen is not None:
                wh = self.windowHandle()
                if wh is not None:
                    wh.setScreen(screen)

                # Восстановление сохраненной позиции с валидацией пересечения с экранами
                pos_data = get_config_value("window.terminal_position")
                applied_pos = False
                if isinstance(pos_data, dict) and "x" in pos_data and "y" in pos_data:
                    target_rect = QRect(int(pos_data["x"]), int(pos_data["y"]), self.width(), self.height())
                    if any(s.availableGeometry().intersects(target_rect) for s in QGuiApplication.screens()):
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
            overlay = TransitionOverlay(
                screen_rect, self.geometry(), "in", target=self
            )
            overlay.start()
            QTimer.singleShot(600, self._greet)

            # Переключение в оверлей, если сохранен данный режим отображения
            if get_config_value("appearance.mode") == "overlay":
                QTimer.singleShot(150, lambda: self.process_input("нормальный облик"))

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if child is None or isinstance(child, QVideoWidget):
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
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._drag_offset is not None:
            pos = self.pos()
            set_config_value("window.terminal_position", {"x": pos.x(), "y": pos.y()})
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and (
            self.isMaximized() or self.isFullScreen()
        ):
            QTimer.singleShot(0, self.showNormal)

    def process_input(self, text: str) -> str:
        return self._flow.handle(text)

    def speak(self, text: str) -> SpeechWindow:
        if self._speech is not None:
            self._speech.close(immediate=True)
        hold_ms = min(5000, max(1200, len(text) * 45))
        parent = self
        if (
            self._overlay_mode
            and self._overlay_window is not None
            and self._overlay_window.isVisible()
        ):
            parent = self._overlay_window
        speech = show_text(text, parent=parent, hold_ms=hold_ms)
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
            self.status.setText("Капри // Голос выключен")
            return "Голосовой ввод отключён."
        else:
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
            self.status.setText("Капри // Выполняет")
            result = self.process_input(command)
            self.status.setText("Капри // Слушает")
            self.speak(result)
            return
        self._arm_voice_command()

    def _voice_command(self, text: str) -> str | None:
        command = command_after_trigger(text)
        if command is not None:
            return command
        if self._flow.awaiting_reply:
            return text.strip()
        if self._voice_armed_until > time.monotonic():
            return text.strip()
        return None

    def _arm_voice_command(self) -> None:
        self._voice_armed_until = time.monotonic() + (
            VOICE_COMMAND_WINDOW_MS / 1000
        )
        self.status.setText("Капри // Слушает")
        self._voice_window_timer.start(VOICE_COMMAND_WINDOW_MS)

    def _disarm_voice_command(self) -> None:
        self._voice_armed_until = 0.0
        self._voice_window_timer.stop()

    def _on_voice_window_expired(self) -> None:
        self._voice_armed_until = 0.0
        self._update_voice_status()

    def _update_voice_status(self) -> None:
        if self._voice.is_listening:
            self.status.setText("Капри // Слушает")
        else:
            self.status.setText(self._default_status)

    def _wake_voice_if_needed(self) -> None:
        if not get_config_value("audio.voice_enabled", True):
            return
        if not self._voice.is_listening and not self._voice.is_busy:
            self._voice.start()

    def _on_voice_listening(self, listening: bool) -> None:
        if not listening:
            self.status.setText(self._default_status)
        else:
            self.status.setText("Капри // Слушает")

    def _on_voice_status(self, text: str) -> None:
        if not text:
            self.status.setText(self._default_status)
        elif text == "Слушаю…":
            self.status.setText("Капри // Слушает")
        elif text == "Распознаю…":
            self.status.setText("Капри // Думает")
        else:
            self.status.setText(f"Капри // {text.upper()}")

    def _toggle_glitches(self) -> str:
        enabled = self._glitches.toggle()
        set_config_value("effects.glitches_enabled", enabled)
        return "Глитчи включены." if enabled else "Глитчи выключены."

    def _wild_glitch(self) -> str:
        self._glitches.wild_glitch(5000)
        return "Капри в восторге! Весь экран глитчит 5 секунд."

    def _on_overlay_moved(self, pos: QPoint) -> None:
        set_config_value("window.overlay_position", {"x": pos.x(), "y": pos.y()})

    def _toggle_capri_overlay(self) -> str:
        if not self._overlay_mode:
            if self._overlay_window is None:
                pose = get_config_value("appearance.overlay_pose", "sit")
                pose_map = {
                    "sit": OVERLAY_SIT,
                    "stay": OVERLAY_STAY,
                    "crouch": OVERLAY_CROUCH,
                }
                pose_file = pose_map.get(pose, OVERLAY_SIT)
                if not pose_file.is_file():
                    pose_file = OVERLAY_SIT

                self._overlay_window = CapriOverlayWindow(
                    pose_file,
                    on_interact=self._inactivity.reset_timer,
                    on_context_menu=self.show_context_menu,
                    on_moved=self._on_overlay_moved,
                )
            old_target = self

            pos_data = get_config_value("window.overlay_position")
            applied_pos = False
            if isinstance(pos_data, dict) and "x" in pos_data and "y" in pos_data:
                target_rect = QRect(
                    int(pos_data["x"]),
                    int(pos_data["y"]),
                    self._overlay_window.width(),
                    self._overlay_window.height(),
                )
                if any(s.availableGeometry().intersects(target_rect) for s in QGuiApplication.screens()):
                    self._overlay_window.move(int(pos_data["x"]), int(pos_data["y"]))
                    applied_pos = True

            if not applied_pos:
                center = self.frameGeometry().center()
                self._overlay_window.move(
                    center.x() - self._overlay_window.width() // 2,
                    center.y() - self._overlay_window.height() // 2,
                )

            new_target = self._overlay_window
            self._overlay_mode = True
            set_config_value("appearance.mode", "overlay")
            msg = "Капри в нормальном облике."
        else:
            old_target = (
                self._overlay_window
                if self._overlay_window is not None
                else self
            )
            new_target = self
            self._overlay_mode = False
            set_config_value("appearance.mode", "terminal")
            msg = "Капри снова в окне."

        self._inactivity.switch_target(old_target, new_target)
        self._inactivity.reset_timer()
        return msg

    def _set_overlay_pose(self, pose: str) -> None:
        """Переключает спрайт оверлея питомца при наличии окна оверлея."""
        if self._overlay_window is not None:
            path = {
                "sit": OVERLAY_SIT,
                "stay": OVERLAY_STAY,
                "crouch": OVERLAY_CROUCH,
            }.get(pose)
            if path is not None and path.is_file():
                self._overlay_window.set_pose_image(pose, path)

    def _on_ollama_talking_start(self) -> None:
        """Переключает Капри в позу stay при общении через локальную модель."""
        self._set_overlay_pose("stay")

    def _on_ollama_talking_end(self) -> None:
        """Возвращает Капри в обычную позу sit после завершения ответа модели."""
        self._set_overlay_pose("sit")

    def _locate_mouse(self) -> str:
        """Вспышка у курсора, молнии в центр, и появление Капри с курсором."""
        return self._inactivity.catch_mouse(
            on_pose_change=self._set_overlay_pose
        )

    def _load_initial_settings(self) -> None:
        """Загружает сохраненные предпочтения конфигурации (монитор, микрофон, глитчи, звук)."""
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

        sfx_vol = get_config_value("audio.sfx_volume", 0.5)
        get_speech_sfx().set_volume(float(sfx_vol))

        media_vol = get_config_value("audio.media_volume", 0.6)
        self._media.set_volume(float(media_vol))

    def get_designated_screen(self) -> QScreen | None:
        """Возвращает основной выбранный монитор или экран окна."""
        if self._designated_screen_name:
            for scr in QGuiApplication.screens():
                if scr.name() == self._designated_screen_name:
                    return scr
        return self.screen() or QGuiApplication.primaryScreen()

    def set_designated_screen(self, screen: QScreen) -> None:
        """Устанавливает основной монитор и перемещает питомца в его центр."""
        self._designated_screen_name = screen.name()
        set_config_value("screen.designated_screen", screen.name())

        target = self._inactivity.current_target_widget
        geo = screen.availableGeometry()

        wh = target.windowHandle()
        if wh is not None:
            wh.setScreen(screen)

        cx = geo.left() + (geo.width() - target.width()) // 2
        cy = geo.top() + (geo.height() - target.height()) // 2
        target.move(cx, cy)
        if self._overlay_mode:
            set_config_value("window.overlay_position", {"x": cx, "y": cy})
        else:
            set_config_value("window.terminal_position", {"x": cx, "y": cy})
        self._inactivity.reset_timer()
        self.speak(f"Монитор: {screen.name()}")

    def set_designated_microphone(self, device: QAudioDevice | None) -> None:
        """Переключает активный микрофон и сохраняет выбор."""
        self._voice.set_device(device)
        desc = device.description() if device and not device.isNull() else ""
        set_config_value("audio.designated_microphone", desc if desc else None)
        name = desc if desc else "По умолчанию"
        self.speak(f"Микрофон: {name}")

    def show_context_menu(self, pos: QPoint) -> None:
        """Контекстное меню настроек монитора, микрофона и режимов питомца."""
        self._inactivity.set_paused(True)
        try:
            menu = QMenu(self)
            menu.setStyleSheet(APP_STYLE)

            # 1. Меню мониторов
            screen_menu = menu.addMenu("🖥  Основной монитор")
            screen_group = QActionGroup(screen_menu)
            screen_group.setExclusive(True)

            current_scr = self.get_designated_screen()
            primary_scr = QGuiApplication.primaryScreen()

            for scr in QGuiApplication.screens():
                geo = scr.geometry()
                name = scr.name()
                extra = []
                if primary_scr and scr.name() == primary_scr.name():
                    extra.append("системный")
                extra_str = f" [{', '.join(extra)}]" if extra else ""
                label = f"{name} ({geo.width()}x{geo.height()}){extra_str}"

                action = screen_menu.addAction(label)
                action.setCheckable(True)
                if current_scr and scr.name() == current_scr.name():
                    action.setChecked(True)
                action.triggered.connect(
                    lambda *_, s=scr: self.set_designated_screen(s)
                )
                screen_group.addAction(action)

            # 2. Меню микрофонов
            mic_menu = menu.addMenu("🎙  Микрофон")
            mic_group = QActionGroup(mic_menu)
            mic_group.setExclusive(True)

            current_mic = self._voice.selected_device
            default_mic = QMediaDevices.defaultAudioInput()
            default_label = (
                f"По умолчанию ({default_mic.description()})"
                if not default_mic.isNull()
                else "По умолчанию"
            )
            def_action = mic_menu.addAction(default_label)
            def_action.setCheckable(True)
            if current_mic is None or current_mic.isNull():
                def_action.setChecked(True)
            def_action.triggered.connect(
                lambda *_: self.set_designated_microphone(None)
            )
            mic_group.addAction(def_action)

            for dev in QMediaDevices.audioInputs():
                if not default_mic.isNull() and dev.id() == default_mic.id():
                    continue
                act = mic_menu.addAction(dev.description())
                act.setCheckable(True)
                if current_mic and dev.id() == current_mic.id():
                    act.setChecked(True)
                act.triggered.connect(
                    lambda *_, d=dev: self.set_designated_microphone(d)
                )
                mic_group.addAction(act)

            menu.addSeparator()

            # 3. Быстрые действия
            overlay_act = menu.addAction(
                "🪟  Окно терминала" if self._overlay_mode else "👁  Нормальный облик"
            )
            overlay_act.triggered.connect(
                lambda *_: self.process_input("нормальный облик")
            )

            glitch_act = menu.addAction("⚡  Экранные глитчи")
            glitch_act.setCheckable(True)
            glitch_act.setChecked(self._glitches.is_enabled)
            glitch_act.triggered.connect(
                lambda *_: self.process_input("глитч")
            )

            voice_act = menu.addAction("🎤  Голосовой ввод")
            voice_act.setCheckable(True)
            voice_act.setChecked(self._voice.is_listening)
            voice_act.triggered.connect(
                lambda *_: self._toggle_voice()
            )

            menu.addSeparator()
            quit_act = menu.addAction("❌  Выход")
            quit_act.triggered.connect(self.close)

            menu.exec(pos)
        finally:
            self._inactivity.set_paused(False)


    def _greet(self) -> None:
        if self._speech is not None:
            return
        if self._closing:
            return
        line = random.choice(STARTUP_LINES).format(user=getpass.getuser())
        self.speak(line)

    def _forget_speech(self, window: SpeechWindow) -> None:
        if self._speech is window:
            self._speech = None

    def _on_media_error(self, error_str: str) -> None:
        self.status.setText(f"Капри // ОШИБКА ВОСПРОИЗВЕДЕНИЯ: {error_str}")

    def _finish_close(self) -> None:
        self._media.stop()
        if self._speech is not None:
            self._speech.close()
        target = self._inactivity.current_target_widget
        if target.isVisible():
            screen = target.screen()
            screen_rect = (
                screen.geometry() if screen is not None else target.geometry()
            )
            overlay = TransitionOverlay(
                screen_rect, target.geometry(), "out", target=target
            )
            overlay.finished.connect(self.close)
            overlay.start()
        else:
            QTimer.singleShot(0, self.close)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._closing or self._media.phase == PHASE_CLOSED:
            self._media.stop()
            super().closeEvent(event)
            return

        try:
            if self._overlay_mode and self._overlay_window is not None:
                pos = self._overlay_window.pos()
                set_config_value("window.overlay_position", {"x": pos.x(), "y": pos.y()})
            else:
                pos = self.pos()
                set_config_value("window.terminal_position", {"x": pos.x(), "y": pos.y()})
        except Exception:
            pass

        if self._overlay_mode:
            self._toggle_capri_overlay()
        self._closing = True
        event.ignore()
        self._voice.cancel()
        self._glitches.stop()
        close_all_speech()
        if self._overlay_window is not None:
            self._overlay_window.close()
        self.speak(GOODBYE_LINE)
        self._media.play_outro()


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from main import main

    raise SystemExit(main())
