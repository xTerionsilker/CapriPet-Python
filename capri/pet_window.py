"""Главное окно Capri: зацикленное видео питомца и ввод команд."""

from __future__ import annotations

import getpass
import os
import random
import re
import shutil
import subprocess
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

from PySide6.QtCore import Qt, QTimer, QUrl
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

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from capri.commands import CommandRegistry
    from capri.glitch import GlitchManager
    from capri.speech import SpeechWindow, show_text
    from capri.static_noise import StaticNoise
    from capri.theme import APP_STYLE
    from capri.voice import VoiceInput
else:
    from .commands import CommandRegistry
    from .glitch import GlitchManager
    from .speech import SpeechWindow, show_text
    from .static_noise import StaticNoise
    from .theme import APP_STYLE
    from .voice import VoiceInput

VIDEO = Path(__file__).resolve().parent.parent / "capri.mp4"
PLAYBACK_RATE = 1.5

STARTUP_LINES = (
    "Молодец, {user}",
    "зови меня просто Capri!!!",
    "...",
)

# Capri выполняет услышанное только после ключевого слова. «Каприкорд»
# распознавание иногда выдаёт как «капри корд», «капри-корд», «Capricorn»
# и т. п.
VOICE_TRIGGER_RE = re.compile(
    r"(?<!\w)(?:"
    r"капри(?:\s*[-–—]?\s*(?:корд|корт|кард|корн|кор))?"
    r"|кэпри"
    r"|capri(?:\s*[-–—]?\s*(?:corn|kord|cord|card|kor))?"
    r")(?!\w)"
)
# Сколько ждать команду после отдельно произнесённого ключевого слова.
VOICE_COMMAND_WINDOW_MS = 3_000
VOICE_LISTENING_STATUS = "СЛУШАЮ «КАПРИ»…"
VOICE_WAITING_STATUS = "ЖДУ КОМАНДУ…"


def _voice_normalized(text: str) -> str:
    return " ".join(text.casefold().split())


class CapriWindow(QWidget):
    """Окно питомца. Напишите или скажите что-нибудь — Capri ответит."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CAPRI")
        self.resize(800, 570)
        self.setMinimumSize(480, 400)
        self.setStyleSheet(APP_STYLE)

        self._speech: SpeechWindow | None = None
        self._greeted = False
        self._lock_pending: list[list[str]] | None = None
        self._voice_armed_until = 0.0
        self._default_status = (
            "// CAPRI В СЕТИ"
            if VIDEO.is_file()
            else f"// ВИДЕО НЕ НАЙДЕНО: {VIDEO.name}"
        )

        # --- видео ---------------------------------------------------------
        self.video = QVideoWidget(self)
        self.video.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.video.setMinimumSize(320, 180)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.6)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.player.errorOccurred.connect(self._on_media_error)

        if VIDEO.is_file():
            self.player.setSource(QUrl.fromLocalFile(str(VIDEO)))
            self.player.setPlaybackRate(PLAYBACK_RATE)
            self.player.play()
        else:
            self.video.hide()

        # --- панель --------------------------------------------------------
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

        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Ctrl+Space"), self, self._toggle_voice)

        self._static = StaticNoise(self)
        self._glitches = GlitchManager(self)
        self._glitches.amplitude_changed.connect(self._static.set_amplitude)

        self._voice = VoiceInput(self)
        self._voice.listening_changed.connect(self._on_voice_listening)
        self._voice.status_changed.connect(self._on_voice_status)
        self._voice.recognized.connect(self._on_voice_text)
        self._voice.failed.connect(self.speak)

        # Окно, в течение которого команду можно произнести отдельно от
        # ключевого слова.
        self._voice_window_timer = QTimer(self)
        self._voice_window_timer.setSingleShot(True)
        self._voice_window_timer.timeout.connect(self._on_voice_window_expired)

        self.commands = CommandRegistry()
        self.commands.register(
            "глитч",
            "включить или выключить экранные глитчи.",
            self._toggle_glitches,
            aliases=(
                "переключить глитч",
                "включить глитч",
                "выключить глитч",
                "глитчи",
                "глюки",
                "переключить глюки",
                "включить глюки",
                "выключить глюки",
                "эффекты",
                "переключить эффекты",
            ),
        )
        self.commands.register(
            "шум",
            "включить или выключить фоновый шум.",
            self._toggle_noise,
            aliases=(
                "переключить шум",
                "включить шум",
                "выключить шум",
                "шипение",
                "переключить шипение",
                "включить шипение",
                "выключить шипение",
                "статика",
                "звук",
                "включить звук",
                "выключить звук",
            ),
        )
        self.commands.register(
            "голос",
            "начать или остановить голосовой ввод.",
            self._toggle_voice,
            aliases=(
                "микрофон",
                "слушать",
                "говорить",
                "голосовой ввод",
                "запись",
                "включить голос",
                "выключить голос",
                "включить микрофон",
                "выключить микрофон",
            ),
        )
        self.commands.register(
            "гугл",
            "найти запрос в Google.",
            self._search_google,
            aliases=(
                "загугли",
                "погугли",
                "гуглить",
                "искать в гугле",
                "найди в гугле",
                "поищи в гугле",
                "поискать в гугле",
                "поиск в гугле",
                "google",
                "искать в google",
                "найди в google",
                "поищи в google",
                "поиск в google",
                "найди в интернете",
                "поищи в интернете",
            ),
            takes_argument=True,
        )
        self.commands.register(
            "ютуб",
            "найти запрос на YouTube.",
            self._search_youtube,
            aliases=(
                "ютьюб",
                "youtube",
                "искать на ютубе",
                "найди на ютубе",
                "найди в ютубе",
                "поищи на ютубе",
                "поищи в ютубе",
                "поискать на ютубе",
                "поиск на ютубе",
                "поиск в ютубе",
                "искать на youtube",
                "найди на youtube",
                "поищи на youtube",
                "поиск на youtube",
            ),
            takes_argument=True,
        )
        self.commands.register(
            "блокировка",
            "заблокировать экран (аналог Super+L).",
            self._lock_screen,
            aliases=(
                "заблокировать",
                "заблокируй",
                "блокировать",
                "заблокировать экран",
                "заблокируй экран",
                "экран блокировки",
                "блокировка экрана",
                "лок",
                "lock",
                "lock screen",
                "super+l",
                "я отойду",
                "отойду",
            ),
        )

        self.input.setFocus()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        if not self._greeted:
            self._greeted = True
            QTimer.singleShot(600, self._greet)

    # --- ввод --------------------------------------------------------------
    def submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.speak(self.process_input(text))

    def process_input(self, text: str) -> str:
        """Обработать строку пользователя. Здесь можно расширять «мозг» Capri."""
        reply = self.commands.dispatch(text)
        if reply is not None:
            return reply
        return f"Ты сказал: {text}"

    def speak(self, text: str) -> SpeechWindow:
        """Показать ``text`` в облачке Capri."""
        if self._speech is not None:
            self._speech.close()
        # Длинным ответам даём чуть больше времени на прочтение.
        hold_ms = min(5000, max(1200, len(text) * 45))
        speech = show_text(text, parent=self, hold_ms=hold_ms)
        self._speech = speech
        speech.destroyed.connect(
            lambda *_, window=speech: self._forget_speech(window)
        )
        return speech

    # --- голос -------------------------------------------------------------
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
        # Прозвучало только ключевое слово — ждём команду в течение окна.
        self._arm_voice_command()

    def _voice_command(self, text: str) -> str | None:
        """Вернуть команду из фразы либо ``None``, если её не было.

        Команда может идти сразу за ключевым словом («капри открой гугл»)
        или прозвучать отдельной фразой в течение ``VOICE_COMMAND_WINDOW_MS``
        после ключевого слова.
        """
        normalized = _voice_normalized(text)
        match = VOICE_TRIGGER_RE.search(normalized)
        if match is not None:
            tokens = text.split()
            consumed = max(1, len(match.group(0).split()))
            before = len(normalized[: match.start()].split())
            # «Дальше уже команда»: всё после ключевого слова.
            return " ".join(tokens[before + consumed:]).strip()
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

    # --- внутреннее --------------------------------------------------------
    def _toggle_glitches(self) -> str:
        enabled = self._glitches.toggle()
        return "Глитчи включены." if enabled else "Глитчи выключены."

    def _toggle_noise(self) -> str:
        enabled = self._static.toggle()
        return "Шум включён." if enabled else "Шум выключен."

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

    # --- блокировка экрана -------------------------------------------------
    def _lock_screen(self) -> str:
        commands = self._lock_commands()
        if not commands:
            return "Не удалось найти способ заблокировать экран."
        self._lock_pending = commands
        QTimer.singleShot(800, self._perform_lock)
        return "Блокирую экран."

    def _perform_lock(self) -> None:
        commands = self._lock_pending
        if not commands:
            return
        self._lock_pending = None
        if not self._run_lock(commands):
            self.speak("Не удалось заблокировать экран.")

    @staticmethod
    def _run_lock(commands: list[list[str]]) -> bool:
        """Попробовать команды блокировки по очереди, пока одна не сработает."""
        for command in commands:
            try:
                result = subprocess.run(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                )
            except subprocess.TimeoutExpired:
                # Блокировщик может работать до разблокировки — считаем успехом.
                return True
            except OSError:
                continue
            if result.returncode == 0:
                return True
        return False

    @staticmethod
    def _lock_commands() -> list[list[str]]:
        """Подобрать команды блокировки экрана текущего окружения."""
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
        candidates: list[list[str]] = []

        if any(name in desktop for name in ("KDE", "PLASMA")):
            qdbus = (
                "qdbus6"
                if shutil.which("qdbus6")
                else "qdbus"
                if shutil.which("qdbus")
                else None
            )
            if qdbus:
                candidates.append(
                    [
                        qdbus,
                        "org.freedesktop.ScreenSaver",
                        "/ScreenSaver",
                        "Lock",
                    ]
                )

        # Универсальный способ через systemd-logind; без ID блокируется
        # сессия вызывающего процесса. Это аналог Super+L.
        candidates.append(["loginctl", "lock-session"])
        candidates.append(["xdg-screensaver", "lock"])
        candidates.append(["gnome-screensaver-command", "-l"])
        candidates.append(["cinnamon-screensaver-command", "-l"])
        candidates.append(["xfce4-screensaver-command", "-l"])
        candidates.append(["light-locker-command", "-l"])

        return [command for command in candidates if shutil.which(command[0])]

    def _greet(self) -> None:
        if self._speech is not None:  # пользователь уже получил ответ
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

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self.player.stop()
        self._voice.cancel()
        self._static.stop()
        self._glitches.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from main import main

    raise SystemExit(main())
