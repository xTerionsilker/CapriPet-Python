"""Главное окно Capri: зацикленное видео питомца и ввод команд."""

from __future__ import annotations

import getpass
import random
from pathlib import Path

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


class CapriWindow(QWidget):
    """Окно питомца. Напишите или скажите что-нибудь — Capri ответит."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CAPRI // ПИТОМЕЦ")
        self.resize(800, 570)
        self.setMinimumSize(480, 400)
        self.setStyleSheet(APP_STYLE)

        self._speech: SpeechWindow | None = None
        self._greeted = False
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
        self.mic.setToolTip("Голосовая команда (Ctrl+Space)")
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

        self.commands = CommandRegistry()
        self.commands.register(
            "глитч",
            "включить или выключить экранные глитчи.",
            self._toggle_glitches,
            aliases=("переключить глитч", "включить глитч", "выключить глитч"),
        )
        self.commands.register(
            "шум",
            "включить или выключить фоновый шум.",
            self._toggle_noise,
            aliases=("переключить шум", "включить шум", "выключить шум"),
        )
        self.commands.register(
            "голос",
            "начать или остановить голосовой ввод.",
            self._toggle_voice,
            aliases=("микрофон", "слушать"),
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
        if self._voice.is_busy:
            return "Подождите, идёт распознавание."
        was_listening = self._voice.is_listening
        self._voice.toggle()
        if self._voice.is_listening:
            return "Слушаю…"
        if was_listening:
            return "Запись остановлена."
        return "Микрофон недоступен."

    def _on_voice_text(self, text: str) -> None:
        self.input.setText(text)
        self.submit()

    def _on_voice_listening(self, listening: bool) -> None:
        self.mic.setText("СТОП" if listening else "ГОЛОС")

    def _on_voice_status(self, text: str) -> None:
        self.status.setText(f"// {text.upper()}" if text else self._default_status)

    # --- внутреннее --------------------------------------------------------
    def _toggle_glitches(self) -> str:
        enabled = self._glitches.toggle()
        return "Глитчи включены." if enabled else "Глитчи выключены."

    def _toggle_noise(self) -> str:
        enabled = self._static.toggle()
        return "Шум включён." if enabled else "Шум выключен."

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
