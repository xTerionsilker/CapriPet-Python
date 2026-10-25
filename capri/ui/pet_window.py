from __future__ import annotations

import getpass
import random
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from capri.core.command_catalog import Handlers, register_commands
    from capri.core.commands import CommandRegistry
    from capri.effects.glitch import GlitchManager
    from capri.core.input_flow import InputFlow
    from capri.integrations.screen_lock import lock_commands, run_lock
    from capri.ui.speech import SpeechWindow, show_text
    from capri.integrations.system_power import power_commands, run_power
    from capri.ui.theme import APP_STYLE
    from capri.audio.voice import VoiceInput
    from capri.core.wake_word import (
        VOICE_COMMAND_WINDOW_MS,
        VOICE_LISTENING_STATUS,
        VOICE_WAITING_STATUS,
        command_after_trigger,
    )
    import capri.integrations.ollama as ollama
    import capri.integrations.spotify as spotify
else:
    from ..core.command_catalog import Handlers, register_commands
    from ..core.commands import CommandRegistry
    from ..effects.glitch import GlitchManager
    from ..core.input_flow import InputFlow
    from ..integrations.screen_lock import lock_commands, run_lock
    from .speech import SpeechWindow, show_text
    from ..integrations.system_power import power_commands, run_power
    from .theme import APP_STYLE
    from ..audio.voice import VoiceInput
    from ..core.wake_word import (
        VOICE_COMMAND_WINDOW_MS,
        VOICE_LISTENING_STATUS,
        VOICE_WAITING_STATUS,
        command_after_trigger,
    )
    from ..integrations import ollama, spotify

ROOT = Path(__file__).resolve().parent.parent.parent
FACES = ROOT / "faces"

START_VIDEO = FACES / "start.mp4"
VIDEO = FACES / "capri.mp4"
END_VIDEO = FACES / "end.mp4"

VIDEOS = (START_VIDEO, VIDEO, END_VIDEO)

VOICES = ROOT / "voices"
START_SOUND = VOICES / "start.mp3"
END_SOUND = VOICES / "end.mp3"

PLAYBACK_RATE = 1.5
SERVICE_PLAYBACK_RATE = 2.0

PHASE_START = "start"
PHASE_MAIN = "main"
PHASE_END = "end"
PHASE_CLOSED = "closed"

STARTUP_LINES = (
    "Молодец, {user}",
    "зови меня просто Capri!!!",
    "...",
)

GOODBYE_LINE = "пока пока чумба"

LOCK_DELAY_MS = 800

POWER_DELAY_MS = 2000

OLLAMA_HISTORY_MESSAGES = 12


class CapriWindow(QWidget):

    spotify_reply = Signal(str)
    ollama_reply = Signal(str)
    ollama_failed = Signal(str)
    power_failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CAPRI")
        self.setFixedSize(800, 540)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setStyleSheet(APP_STYLE)

        self._drag_offset: QPoint | None = None

        self._speech: SpeechWindow | None = None
        self._greeted = False
        self._lock_pending: list[list[str]] | None = None
        self._power_pending: list[list[str]] | None = None
        self._voice_armed_until = 0.0
        self._ollama_history: list[dict[str, str]] = []
        self._ollama_pending = ""
        self._ollama_busy = False
        self._phase = PHASE_MAIN
        self._closing = False
        self._outro_video_done = True
        self._outro_sound_done = True
        self._default_status = (
            "// CAPRI В СЕТИ"
            if VIDEO.is_file()
            else f"// ВИДЕО НЕ НАЙДЕНО: {VIDEO.relative_to(ROOT)}"
        )

        self.commands = CommandRegistry()
        self._flow = InputFlow(self.commands, self)

        self._build_video()
        self._build_sound()
        self._build_controls()
        self._build_shortcuts()
        self._build_effects()
        self._build_voice()
        self._register_commands()
        self.spotify_reply.connect(self.speak)
        self.ollama_reply.connect(self._on_ollama_reply)
        self.ollama_failed.connect(self._on_ollama_failed)
        self.power_failed.connect(self.speak)

        self.input.setFocus()

    def _build_video(self) -> None:
        self.video = QVideoWidget(self)
        self.video.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.video.setMinimumSize(320, 180)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.6)
        self.audio.setMuted(True)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.errorOccurred.connect(self._on_media_error)
        self.player.mediaStatusChanged.connect(self._on_media_status)

        if not any(path.is_file() for path in VIDEOS):
            self.video.hide()
            return
        if START_VIDEO.is_file():
            self._play_intro()
        else:
            self._play_main()

    def _build_sound(self) -> None:
        self.sound = QMediaPlayer(self)
        self.sound_audio = QAudioOutput(self)
        self.sound_audio.setVolume(0.6)
        self.sound.setAudioOutput(self.sound_audio)
        self.sound.errorOccurred.connect(self._on_sound_error)
        self.sound.mediaStatusChanged.connect(self._on_sound_status)

        if START_SOUND.is_file():
            self._play_sound(START_SOUND)

    def _play_sound(self, path: Path) -> None:
        self.sound.setLoops(QMediaPlayer.Loops.Once)
        self.sound.setSource(QUrl.fromLocalFile(str(path)))
        self.sound.play()

    def _play_source(
        self, path: Path, loops: QMediaPlayer.Loops, rate: float
    ) -> None:
        self.player.setLoops(loops)
        self.player.setPlaybackRate(rate)
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def _play_intro(self) -> None:
        self._phase = PHASE_START
        self.video.show()
        self._play_source(
            START_VIDEO, QMediaPlayer.Loops.Once, SERVICE_PLAYBACK_RATE
        )

    def _play_main(self) -> None:
        self._phase = PHASE_MAIN
        if not VIDEO.is_file():
            self.video.hide()
            return
        self.video.show()
        self._play_source(VIDEO, QMediaPlayer.Loops.Infinite, PLAYBACK_RATE)

    def _play_outro(self) -> None:
        have_video = END_VIDEO.is_file()
        have_sound = END_SOUND.is_file()
        self._outro_video_done = not have_video
        self._outro_sound_done = not have_sound

        if not have_video and not have_sound:
            self._finish_close()
            return

        self._phase = PHASE_END
        if have_video:
            self.video.show()
            self._play_source(
                END_VIDEO, QMediaPlayer.Loops.Once, SERVICE_PLAYBACK_RATE
            )
        if have_sound:
            self._play_sound(END_SOUND)
        self._maybe_finish_outro()

    def _maybe_finish_outro(self) -> None:
        if self._phase != PHASE_END:
            return
        if self._outro_video_done and self._outro_sound_done:
            self._finish_close()

    def _build_controls(self) -> None:
        panel = QWidget(self)
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 12, 16, 14)
        panel_layout.setSpacing(8)

        self.status = QLabel(self._default_status, panel)
        self.status.setObjectName("status")

        self.input = QLineEdit(panel)
        self.input.setPlaceholderText("Скажи что-нибудь Capri…")
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(self.submit)

        self.mic = QPushButton("ГОЛОС", panel)
        self.mic.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic.setToolTip(
            "Голосовой ввод (Ctrl+Space). Команда — после слова «Капри»"
        )
        self.mic.clicked.connect(self._toggle_voice)

        send = QPushButton("ОТПРАВИТЬ", panel)
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.clicked.connect(self.submit)

        prompt = QLabel(">", panel)
        prompt.setObjectName("prompt")

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(prompt)
        row.addWidget(self.input, 1)
        row.addWidget(self.mic)
        row.addWidget(send)

        panel_layout.addWidget(self.status)
        panel_layout.addLayout(row)

        accent = QFrame(self)
        accent.setObjectName("accent")
        accent.setFixedHeight(3)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.video, 1)
        root.addWidget(accent)
        root.addWidget(panel)

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Ctrl+Space"), self, self._toggle_voice)

    def _build_effects(self) -> None:
        self._glitches = GlitchManager(self)

    def _build_voice(self) -> None:
        self._voice = VoiceInput(self)
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
                ask_ollama=self._ask_ollama,
                search_google=self._search_google,
                search_youtube=self._search_youtube,
                spotify_play=self._spotify_play,
                spotify_pause=self._spotify_pause,
                spotify_resume=self._spotify_resume,
                spotify_next=self._spotify_next,
                spotify_previous=self._spotify_previous,
                lock_screen=self._lock_screen,
                power_off=self._power_off,
                suspend=self._suspend,
                reboot=self._reboot,
            ),
        )

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        if not self._greeted:
            self._greeted = True
            QTimer.singleShot(600, self._greet)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if child is None or isinstance(child, QVideoWidget):
                handle = self.windowHandle()
                if handle is not None and hasattr(handle, "startSystemMove"):
                    handle.startSystemMove(event)
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

    def submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.speak(self.process_input(text))

    def process_input(self, text: str) -> str:
        return self._flow.handle(text)

    def speak(self, text: str) -> SpeechWindow:
        if self._speech is not None:
            self._speech.close()
        hold_ms = min(5000, max(1200, len(text) * 45))
        speech = show_text(text, parent=self, hold_ms=hold_ms)
        self._speech = speech
        speech.destroyed.connect(
            lambda *_, window=speech: self._forget_speech(window)
        )
        return speech

    def _toggle_voice(self) -> str:
        if self._voice.is_listening:
            self._voice.stop()
            self._disarm_voice_command()
            return "Голосовой ввод выключен."
        if self._voice.is_busy:
            return "Подождите, идёт распознавание."
        self._voice.start()
        if self._voice.is_listening:
            return "Слушаю. Скажи «Капри» и команду."
        return "Микрофон недоступен."

    def _on_voice_text(self, text: str) -> None:
        command = self._voice_command(text)
        if command is None:
            return
        if command:
            self._disarm_voice_command()
            self._update_voice_status()
            self.speak(self.process_input(command))
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
        self.status.setText(f"// {VOICE_WAITING_STATUS}")
        self._voice_window_timer.start(VOICE_COMMAND_WINDOW_MS)

    def _disarm_voice_command(self) -> None:
        self._voice_armed_until = 0.0
        self._voice_window_timer.stop()

    def _on_voice_window_expired(self) -> None:
        self._voice_armed_until = 0.0
        self._update_voice_status()

    def _update_voice_status(self) -> None:
        if self._voice.is_listening:
            self.status.setText(f"// {VOICE_LISTENING_STATUS}")
        else:
            self.status.setText(self._default_status)

    def _on_voice_listening(self, listening: bool) -> None:
        self.mic.setText("СТОП" if listening else "ГОЛОС")
        if not listening:
            self._disarm_voice_command()

    def _on_voice_status(self, text: str) -> None:
        if not text:
            self.status.setText(self._default_status)
        elif text == "Слушаю…":
            if self._voice_armed_until > time.monotonic():
                self.status.setText(f"// {VOICE_WAITING_STATUS}")
            else:
                self.status.setText(f"// {VOICE_LISTENING_STATUS}")
        else:
            self.status.setText(f"// {text.upper()}")

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

    def _ask_ollama(self, prompt: str) -> str:
        prompt = prompt.strip()
        if not prompt:
            return "Скажи, о чём спросить: «слушай <текст>»."
        if self._ollama_busy:
            return "Ещё думаю над прошлым — подожди."
        history = list(self._ollama_history)
        self._ollama_pending = prompt
        self._ollama_busy = True
        threading.Thread(
            target=self._ask_ollama_worker,
            args=(prompt, history),
            name="capri-ollama",
            daemon=True,
        ).start()
        return "Думаю…"

    def _ask_ollama_worker(
        self, prompt: str, history: list[dict[str, str]]
    ) -> None:
        try:
            answer = ollama.ask(prompt, history=history)
        except ollama.OllamaError as error:
            self.ollama_failed.emit(str(error))
            return
        except Exception:
            self.ollama_failed.emit("Локальная модель не ответила.")
            return
        self.ollama_reply.emit(answer)

    def _on_ollama_reply(self, answer: str) -> None:
        prompt = self._ollama_pending
        self._finish_ollama()
        if prompt:
            self._ollama_history.append({"role": "user", "content": prompt})
            self._ollama_history.append(
                {"role": "assistant", "content": answer}
            )
            del self._ollama_history[:-OLLAMA_HISTORY_MESSAGES]
        self.speak(answer)

    def _on_ollama_failed(self, message: str) -> None:
        self._finish_ollama()
        self.speak(message)

    def _finish_ollama(self) -> None:
        self._ollama_busy = False
        self._ollama_pending = ""

    def _spotify_play(self, query: str) -> str:
        query = query.strip()
        if not query:
            return "Что включить? Скажи: «спотифай <запрос>»."
        threading.Thread(
            target=self._spotify_play_worker,
            args=(query,),
            name="capri-spotify",
            daemon=True,
        ).start()
        return "Ищу в Spotify…"

    def _spotify_play_worker(self, query: str) -> None:
        try:
            message = spotify.play(query)
        except Exception:
            message = "Не удалось обратиться к Spotify."
        self.spotify_reply.emit(message)

    def _spotify_pause(self) -> str:
        return spotify.pause()

    def _spotify_resume(self) -> str:
        return spotify.resume()

    def _spotify_next(self) -> str:
        return spotify.next_track()

    def _spotify_previous(self) -> str:
        return spotify.previous_track()

    def _lock_screen(self) -> str:
        commands = lock_commands()
        if not commands:
            return "Не удалось найти способ заблокировать экран."
        self._lock_pending = commands
        QTimer.singleShot(LOCK_DELAY_MS, self._perform_lock)
        return "Блокирую экран."

    def _perform_lock(self) -> None:
        commands = self._lock_pending
        if not commands:
            return
        self._lock_pending = None
        if not run_lock(commands):
            self.speak("Не удалось заблокировать экран.")

    def _power_off(self) -> str:
        return self._queue_power("poweroff", "Выключаю ПК.")

    def _suspend(self) -> str:
        return self._queue_power("suspend", "Ухожу в спящий режим.")

    def _reboot(self) -> str:
        return self._queue_power("reboot", "Перезагружаю ПК.")

    def _queue_power(self, action: str, message: str) -> str:
        commands = power_commands(action)
        if not commands:
            return "Не удалось найти способ выполнить это действие."
        self._power_pending = commands
        QTimer.singleShot(POWER_DELAY_MS, self._perform_power)
        return message

    def _perform_power(self) -> None:
        commands = self._power_pending
        if not commands:
            return
        self._power_pending = None
        threading.Thread(
            target=self._power_worker,
            args=(commands,),
            name="capri-power",
            daemon=True,
        ).start()

    def _power_worker(self, commands: list[list[str]]) -> None:
        if not run_power(commands):
            self.power_failed.emit("Не удалось выполнить действие.")

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

    def _on_media_error(self, *_args) -> None:
        self.status.setText(
            f"// ОШИБКА ВОСПРОИЗВЕДЕНИЯ: {self.player.errorString()}"
        )
        if self._phase == PHASE_START:
            QTimer.singleShot(0, self._play_main)
        elif self._phase == PHASE_END:
            self._outro_video_done = True
            QTimer.singleShot(0, self._maybe_finish_outro)

    def _on_media_status(self, status) -> None:
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if self._phase == PHASE_START:
            self._play_main()
        elif self._phase == PHASE_END:
            self._outro_video_done = True
            self._maybe_finish_outro()

    def _on_sound_error(self, *_args) -> None:
        if self._phase == PHASE_END:
            self._outro_sound_done = True
            QTimer.singleShot(0, self._maybe_finish_outro)

    def _on_sound_status(self, status) -> None:
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if self._phase == PHASE_END:
            self._outro_sound_done = True
            self._maybe_finish_outro()

    def _finish_close(self) -> None:
        self._phase = PHASE_CLOSED
        self.player.stop()
        self.sound.stop()
        if self._speech is not None:
            self._speech.close()
        QTimer.singleShot(0, self.close)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._closing or self._phase == PHASE_CLOSED:
            self.player.stop()
            self.sound.stop()
            super().closeEvent(event)
            return
        self._closing = True
        event.ignore()
        self._voice.cancel()
        self._glitches.stop()
        self.speak(GOODBYE_LINE)
        self._play_outro()


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from main import main

    raise SystemExit(main())
