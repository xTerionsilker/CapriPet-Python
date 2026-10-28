from __future__ import annotations

import getpass
import random
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import (
    QActionGroup,
    QColor,
    QGuiApplication,
    QKeySequence,
    QPainter,
    QPixmap,
    QScreen,
    QShortcut,
)
from PySide6.QtMultimedia import QAudioDevice, QMediaDevices
from PySide6.QtWidgets import (
    QMenu,
    QWidget,
)

from ..audio.voice import VoiceInput
from ..controllers import ActionBridge, InactivityManager
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
from ..effects.transition_fx import pick_palette_color
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

        self._pixmaps: dict[str, QPixmap] = {}
        self._load_all_poses()
        self._current_pose = "sit"
        self._pixmap = self._pixmaps.get("sit") or next(iter(self._pixmaps.values()))
        self.setFixedSize(self._pixmap.size())

        self._drag_offset: QPoint | None = None
        self._speech: SpeechWindow | None = None
        self._greeted = False
        self._spawn_glitch_ticks = 18
        self._startup_overlay: TransitionOverlay | None = None
        self._voice_armed_until = 0.0
        self._closing = False
        self._designated_screen_name: str | None = None

        # Таймер анимации пиксельных глитчей
        self._glitch_timer = QTimer(self)
        self._glitch_timer.setInterval(80)
        self._glitch_timer.timeout.connect(self._on_glitch_tick)

        self.commands = CommandRegistry()
        self._flow = InputFlow(self.commands, self)
        self._actions = ActionBridge(self)
        self._actions.speech_requested.connect(self.speak)
        self._actions.ollama_started.connect(self._on_ollama_talking_start)
        self._actions.ollama_finished.connect(self._on_ollama_talking_end)

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
        inactivity_ms = get_config_value("behavior.inactivity_timeout_ms", 5000)
        self._inactivity.set_timeout_ms(int(inactivity_ms))

        voice_enabled = get_config_value("audio.voice_enabled", True)
        if voice_enabled:
            self._voice.start()
        self._inactivity.start()

    def _load_pixmap(self, name: str, path: Path) -> QPixmap:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            pixmap = QPixmap(420, 420)
        target_width = max(1, int(pixmap.width() / 1.5))
        target_height = max(1, int(pixmap.height() / 1.5))
        scaled = pixmap.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._pixmaps[name] = scaled
        return scaled

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
            fallback = QPixmap(280, 280)
            fallback.fill(Qt.GlobalColor.transparent)
            self._pixmaps["sit"] = fallback

    def set_pose(self, pose: str) -> None:
        """Переключает спрайт позы питомца."""
        if pose not in self._pixmaps:
            pose_path = {
                "sit": OVERLAY_SIT,
                "stay": OVERLAY_STAY,
                "crouch": OVERLAY_CROUCH,
            }.get(pose)
            if pose_path is not None and pose_path.is_file():
                self._load_pixmap(pose, pose_path)
        if pose in self._pixmaps:
            self._current_pose = pose
            self._pixmap = self._pixmaps[pose]
            self.setFixedSize(self._pixmap.size())
            self.update()

    def set_pose_image(self, pose_name: str, path: Path) -> None:
        """Переключает спрайт позы по пути к файлу."""
        self._load_pixmap(pose_name, path)
        self.set_pose(pose_name)

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
                locate_mouse=self._locate_mouse,
            ),
        )

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
            try:
                get_speech_sfx().play_swoosh()
            except Exception:
                pass

    def _reveal_on_startup(self) -> None:
        """Переход Капри из позы приземления в позу покоя на пике вспышки."""
        self.set_pose("sit")
        self.update()
        QTimer.singleShot(600, self._greet)

    def _on_startup_finished(self) -> None:
        self._startup_overlay = None
        self.set_pose("sit")
        self.update()

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._glitch_timer.stop()
        super().hideEvent(event)

    def _on_glitch_tick(self) -> None:
        if self._spawn_glitch_ticks > 0:
            self._glitch_timer.setInterval(35)
        else:
            self._glitch_timer.setInterval(random.randint(60, 110))
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        w = self._pixmap.width()
        h = self._pixmap.height()
        if w <= 0 or h <= 0:
            painter.end()
            return

        is_spawning = self._spawn_glitch_ticks > 0
        if is_spawning:
            self._spawn_glitch_ticks -= 1

        active_glitch = is_spawning or (random.random() < 0.55)

        # 1. Отрисовка базового спрайта
        slice_chance = 0.90 if is_spawning else 0.50
        if active_glitch and random.random() < slice_chance:
            sy = (random.randint(0, max(0, h - 16)) // 4) * 4
            sh = random.choice((6, 8, 12, 16, 24)) if is_spawning else random.choice((6, 8, 12, 16))
            dx = random.choice((-24, -18, -12, 12, 18, 24)) if is_spawning else random.choice((-16, -12, -8, 8, 12, 16))
            if sy > 0:
                painter.drawPixmap(0, 0, self._pixmap, 0, 0, w, sy)
            painter.drawPixmap(dx, sy, self._pixmap, 0, sy, w, sh)
            bottom_y = sy + sh
            if bottom_y < h:
                painter.drawPixmap(
                    0, bottom_y, self._pixmap, 0, bottom_y, w, h - bottom_y
                )
        else:
            painter.drawPixmap(0, 0, self._pixmap)

        # 2. Наложение крупных глитчей в фирменной палитре Капри
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceAtop
        )

        def get_glitch_color(alpha_min: int = 180, alpha_max: int = 255) -> QColor:
            c = QColor(pick_palette_color())
            c.setAlpha(random.randint(alpha_min, alpha_max))
            return c

        # а) Горизонтальные глитч-полосы
        bar_count = (
            random.randint(4, 8)
            if is_spawning
            else (
                random.randint(2, 5)
                if active_glitch
                else (random.randint(1, 2) if random.random() < 0.5 else 0)
            )
        )
        for _ in range(bar_count):
            by = (random.randint(0, max(0, h - 8)) // 4) * 4
            bh = random.choice((4, 6, 8, 12))
            bw = (random.randint(w // 4, w) // 4) * 4
            bx = (random.randint(0, max(0, w - bw)) // 4) * 4
            color = get_glitch_color(190, 255)
            painter.fillRect(bx, by, bw, bh, color)

        # б) Пиксельные блоки
        block_count = (
            random.randint(7, 14)
            if is_spawning
            else (
                random.randint(4, 9)
                if active_glitch
                else random.randint(1, 4)
            )
        )
        for _ in range(block_count):
            bw = random.choice((8, 12, 16, 20, 28))
            bh = random.choice((6, 8, 12, 16))
            bx = (random.randint(0, max(0, w - bw)) // 4) * 4
            by = (random.randint(0, max(0, h - bh)) // 4) * 4
            color = get_glitch_color(180, 255)
            painter.fillRect(bx, by, bw, bh, color)

        # в) Пиксельные шумовые квадраты
        noise_count = (
            random.randint(12, 24)
            if is_spawning
            else (
                random.randint(6, 16)
                if active_glitch
                else random.randint(2, 6)
            )
        )
        for _ in range(noise_count):
            nx = (random.randint(0, max(0, w - 4)) // 4) * 4
            ny = (random.randint(0, max(0, h - 4)) // 4) * 4
            color = get_glitch_color(190, 255)
            painter.fillRect(nx, ny, 4, 4, color)

        # 3. Выступающие за силуэт искры
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )
        spark_chance = 0.90 if is_spawning else 0.65
        if active_glitch and random.random() < spark_chance:
            sparks_n = random.randint(4, 7) if is_spawning else random.randint(2, 4)
            for _ in range(sparks_n):
                ex = (random.randint(0, max(0, w - 8)) // 4) * 4
                ey = (random.randint(0, max(0, h - 8)) // 4) * 4
                ew = random.choice((4, 8, 12)) if is_spawning else random.choice((4, 8))
                eh = random.choice((4, 6, 8)) if is_spawning else random.choice((4, 6))
                spark_color = get_glitch_color(200, 255)
                painter.fillRect(ex, ey, ew, eh, spark_color)

        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._inactivity.reset_timer()
        if event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
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
            set_config_value("window.position", {"x": pos.x(), "y": pos.y()})
            set_config_value("window.overlay_position", {"x": pos.x(), "y": pos.y()})
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
        self.speak("Что?")

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

    def _wild_glitch(self) -> str:
        self._glitches.wild_glitch(5000)
        return "Капри в восторге! Весь экран глитчит 5 секунд."

    def _on_ollama_talking_start(self) -> None:
        self.set_pose("stay")

    def _on_ollama_talking_end(self) -> None:
        self.set_pose("sit")

    def _locate_mouse(self) -> str:
        return self._inactivity.catch_mouse(
            on_pose_change=self.set_pose
        )

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

        sfx_vol = get_config_value("audio.sfx_volume", 0.5)
        get_speech_sfx().set_volume(float(sfx_vol))

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

    def show_context_menu(self, pos: QPoint) -> None:
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

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._closing:
            super().closeEvent(event)
            return

        try:
            pos = self.pos()
            set_config_value("window.position", {"x": pos.x(), "y": pos.y()})
            set_config_value("window.overlay_position", {"x": pos.x(), "y": pos.y()})
        except Exception:
            pass

        self._closing = True
        event.ignore()
        self._voice.cancel()
        self._glitches.stop()
        close_all_speech()
        self.speak(GOODBYE_LINE)

        screen = self.screen()
        screen_rect = (
            screen.geometry() if screen is not None else self.geometry()
        )
        overlay = TransitionOverlay(
            screen_rect, self.geometry(), "out", target=self
        )
        overlay.finished.connect(self.close)
        overlay.start()


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from main import main

    raise SystemExit(main())
