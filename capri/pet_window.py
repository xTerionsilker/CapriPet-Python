"""Capri's main window: a looping character video plus a text input."""

from __future__ import annotations

import getpass
import random
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
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
from .theme import APP_STYLE

VIDEO = Path(__file__).resolve().parent.parent / "capri.mp4"

STARTUP_LINES = (
    "Good boy, {user}",
    "just call me Capri!!!",
    "...",
)


class CapriWindow(QWidget):
    """The pet window. Type something to get a spoken reply from Capri."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CAPRI // PET")
        self.resize(800, 570)
        self.setMinimumSize(480, 400)
        self.setStyleSheet(APP_STYLE)

        self._speech: SpeechWindow | None = None
        self._greeted = False

        # --- video ---------------------------------------------------------
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
            self.player.play()
        else:
            self.video.hide()

        # --- panel ---------------------------------------------------------
        panel = QWidget(self)
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 12, 16, 14)
        panel_layout.setSpacing(8)

        self.status = QLabel(
            "// CAPRI ONLINE" if VIDEO.is_file()
            else f"// VIDEO NOT FOUND: {VIDEO.name}",
            panel,
        )
        self.status.setObjectName("status")

        self.input = QLineEdit(panel)
        self.input.setPlaceholderText("Say something to Capri…")
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(self.submit)

        send = QPushButton("SEND", panel)
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.clicked.connect(self.submit)

        glow = QGraphicsDropShadowEffect(send)
        glow.setBlurRadius(28)
        glow.setOffset(0, 0)
        glow.setColor(QColor(57, 255, 106, 150))
        send.setGraphicsEffect(glow)

        prompt = QLabel(">", panel)
        prompt.setObjectName("prompt")

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(prompt)
        row.addWidget(self.input, 1)
        row.addWidget(send)

        panel_layout.addWidget(self.status)
        panel_layout.addLayout(row)

        accent = QFrame(self)
        accent.setObjectName("accent")
        accent.setFixedHeight(2)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.video, 1)
        root.addWidget(accent)
        root.addWidget(panel)

        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

        self._glitches = GlitchManager(self)

        self.commands = CommandRegistry()
        self.commands.register(
            "glitch",
            "turn the screen glitches on or off.",
            self._toggle_glitches,
            aliases=("turn glitch",),
        )

        self.input.setFocus()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        if not self._greeted:
            self._greeted = True
            QTimer.singleShot(600, self._greet)

    # --- input -------------------------------------------------------------
    def submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.speak(self.process_input(text))

    def process_input(self, text: str) -> str:
        """Handle a line of user input. Extend this to build your pet's brain."""
        reply = self.commands.dispatch(text)
        if reply is not None:
            return reply
        return f"You said: {text}"

    def speak(self, text: str) -> SpeechWindow:
        """Show ``text`` in Capri's speech bubble."""
        if self._speech is not None:
            self._speech.close()
        # Give longer replies a little more reading time.
        hold_ms = min(5000, max(1200, len(text) * 45))
        speech = show_text(text, parent=self, hold_ms=hold_ms)
        self._speech = speech
        speech.destroyed.connect(
            lambda *_, window=speech: self._forget_speech(window)
        )
        return speech

    # --- internals ---------------------------------------------------------
    def _toggle_glitches(self) -> str:
        enabled = self._glitches.toggle()
        return "Glitches ON." if enabled else "Glitches OFF."

    def _greet(self) -> None:
        if self._speech is not None:  # user already got a reply
            return
        line = random.choice(STARTUP_LINES).format(user=getpass.getuser())
        self.speak(line)

    def _forget_speech(self, window: SpeechWindow) -> None:
        if self._speech is window:
            self._speech = None

    def _on_media_error(self, *_args) -> None:
        self.status.setText(f"// PLAYBACK ERROR: {self.player.errorString()}")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self.player.stop()
        self._glitches.stop()
        super().closeEvent(event)
