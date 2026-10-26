from __future__ import annotations

import getpass
import random
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..audio.voice import VoiceInput
from ..core.command_catalog import Handlers, register_commands
from ..core.commands import CommandRegistry
from ..core.input_flow import InputFlow
from ..core.wake_word import (
    VOICE_COMMAND_WINDOW_MS,
    command_after_trigger,
)
from ..effects.glitch import GlitchManager
from .action_bridge import ActionBridge
from .cursor_manager import get_mouse_position, move_mouse_to_center
from .inactivity_manager import InactivityManager
from .media_controller import MediaController, PHASE_CLOSED
from .overlay_window import CapriOverlayWindow
from .speech import SpeechWindow, close_all as close_all_speech, show_text
from .theme import APP_STYLE
from .transition import TransitionOverlay

ROOT = Path(__file__).resolve().parent.parent.parent
OVERLAY_ASSET = ROOT / "assets" / "capri_pet.png"

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

        self.commands = CommandRegistry()
        self._flow = InputFlow(self.commands, self)
        self._actions = ActionBridge(self)
        self._actions.speech_requested.connect(self.speak)

        self._build_ui()
        self._media = MediaController(self, self.video)
        self._media.error_occurred.connect(self._on_media_error)
        self._media.outro_completed.connect(self._finish_close)

        self._build_shortcuts()
        self._glitches = GlitchManager(self)
        self._build_voice()
        self._register_commands()

        self._inactivity = InactivityManager(
            main_window=self,
            get_overlay=lambda: self._overlay_window,
            is_overlay_mode=lambda: self._overlay_mode,
            is_closing=lambda: self._closing or self._media.phase == PHASE_CLOSED,
            on_wake_voice=self._wake_voice_if_needed,
        )

        self._media.start_playback()
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
        self._voice = VoiceInput(always_on=True)
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
                search_google=self._search_google,
                search_youtube=self._search_youtube,
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
            screen = self.screen()
            screen_rect = (
                screen.geometry() if screen is not None else self.geometry()
            )
            overlay = TransitionOverlay(
                screen_rect, self.geometry(), "in", target=self
            )
            overlay.start()
            QTimer.singleShot(600, self._greet)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
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

    def _show_help(self) -> None:
        close_all_speech()
        hold_ms = 6000
        delay = 400
        texts = [
            "помощь (также: что ты умеешь?, команды, справка…) — "
            "показать этот список.",
        ]
        for command in self.commands._commands:
            argument = " <запрос>" if command.takes_argument else ""
            aliases = (
                f" (также: {', '.join(command.aliases)})"
                if command.aliases
                else ""
            )
            texts.append(
                f"{command.name}{argument}{aliases} — {command.description}"
            )

        def show_one(text: str) -> None:
            show_text(text, parent=self, hold_ms=hold_ms)

        for index, text in enumerate(texts):
            QTimer.singleShot(index * delay, lambda t=text: show_one(t))

    def speak(self, text: str) -> SpeechWindow:
        if self._speech is not None:
            self._speech.close()
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
        if not self._voice.is_listening:
            self._voice.start()
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
            found = self.commands.find(command)
            if found is not None and found is self.commands._help:
                self.status.setText("Капри // Выполняет")
                self._show_help()
                self.status.setText("Капри // Слушает")
                return
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
        return "Глитчи включены." if enabled else "Глитчи выключены."

    def _wild_glitch(self) -> str:
        self._glitches.wild_glitch(5000)
        return "Капри в восторге! Весь экран глитчит 5 секунд."

    def _search_google(self, query: str) -> str:
        query = query.strip()
        if not query:
            return "Что искать в Google? Скажи: «гугл <запрос>»."
        webbrowser.open(
            f"https://www.google.com/search?q={quote_plus(query)}"
        )
        return f"Ищу в Google: {query}"

    def _search_youtube(self, query: str) -> str:
        query = query.strip()
        if not query:
            return "Что искать на YouTube? Скажи: «ютуб <запрос>»."
        webbrowser.open(
            "https://www.youtube.com/results?"
            f"search_query={quote_plus(query)}"
        )
        return f"Ищу на YouTube: {query}"

    def _toggle_capri_overlay(self) -> str:
        if not self._overlay_mode:
            if self._overlay_window is None:
                self._overlay_window = CapriOverlayWindow(
                    OVERLAY_ASSET, on_interact=self._inactivity.reset_timer
                )
            old_target = self
            center = self.frameGeometry().center()
            self._overlay_window.move(
                center.x() - self._overlay_window.width() // 2,
                center.y() - self._overlay_window.height() // 2,
            )
            new_target = self._overlay_window
            self._overlay_mode = True
            msg = "Капри в нормальном облике."
        else:
            old_target = (
                self._overlay_window
                if self._overlay_window is not None
                else self
            )
            new_target = self
            self._overlay_mode = False
            msg = "Капри снова в окне."

        self._inactivity.switch_target(old_target, new_target)
        self._inactivity.reset_timer()
        return msg

    def _locate_mouse(self) -> str:
        """Появляется прямо на курсоре мыши и телепортируется с ним в центр экрана."""
        cursor_pos = get_mouse_position()
        target = self._inactivity.current_target_widget

        # Определяем экран, на котором находится курсор мыши
        screen = None
        for scr in QGuiApplication.screens():
            if scr.geometry().contains(cursor_pos):
                screen = scr
                break
        if screen is None:
            screen = target.screen() or QGuiApplication.primaryScreen()

        geo = screen.availableGeometry() if screen is not None else target.geometry()

        # 1. Позиция прямо в курсоре мыши (центрируем виджет относительно курсора)
        mouse_rect = QRect(
            cursor_pos.x() - target.width() // 2,
            cursor_pos.y() - target.height() // 2,
            target.width(),
            target.height(),
        )

        # 2. Позиция в центре экрана
        center_x = geo.left() + (geo.width() - target.width()) // 2
        center_y = geo.top() + (geo.height() - target.height()) // 2
        center_rect = QRect(center_x, center_y, target.width(), target.height())

        def move_mouse() -> None:
            try:
                move_mouse_to_center()
            except Exception:
                pass

        # Если питомец уже виден в другом месте, мгновенно перемещаем в точку мыши
        target.setGeometry(mouse_rect)
        target.show()
        target.raise_()

        # Запускаем телепортацию из позиции мыши в центр экрана вместе с курсором
        self._inactivity.teleport_target(
            target=target,
            from_rect=mouse_rect,
            to_rect=center_rect,
            on_peak_in=move_mouse,
            on_finished=move_mouse,
        )

        self._inactivity.reset_timer()
        return "Поймала мышку!"


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
