#!/usr/bin/env python3
"""A tiny Tamagotchi: a looping character video plus a text input.

The window shows capri.mp4 on repeat. Type something below the video and the
program receives it in ``Tamagotchi.process_input`` — replace or extend that
method to plug in your own logic (an LLM, a state machine, ...).

Quit with Ctrl+Q.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

VIDEO = Path(__file__).resolve().with_name("capri.mp4")

STYLE = """
QWidget {
    background: #050408;
    color: #e7f9ea;
    font-family: "JetBrains Mono", "DejaVu Sans Mono", monospace;
    font-size: 13px;
}
QVideoWidget { background: #000; border: none; }
#accent {
    border: none;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #39ff6a, stop:0.5 #a259ff, stop:1 #ff1e46);
}
#panel { background: #0b0a10; }
#panel QLabel { background: transparent; }
#prompt { color: #39ff6a; font-weight: 700; font-size: 16px; }
#message { color: #cfe9d3; font-size: 13px; }
QLineEdit {
    background: #0f0e15;
    border: 1px solid #342a44;
    border-radius: 8px;
    padding: 9px 12px;
    color: #eaffef;
    placeholder-text-color: #5f6b62;
    selection-background-color: #ff1e46;
    selection-color: #050408;
}
QLineEdit:focus { border: 1px solid #39ff6a; background: #121019; }
QPushButton {
    background: #39ff6a;
    color: #05070a;
    border: none;
    border-radius: 8px;
    padding: 9px 22px;
    font-weight: 800;
    letter-spacing: 2px;
}
QPushButton:hover { background: #7dffa0; }
QPushButton:pressed { background: #12c744; }
"""


class Tamagotchi(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CAPRI // PET")
        self.resize(800, 570)
        self.setMinimumSize(480, 400)
        self.setStyleSheet(STYLE)

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

        self.message = QLabel(
            "Say something to Capri…" if VIDEO.is_file()
            else f"Video not found: {VIDEO.name}",
            panel,
        )
        self.message.setObjectName("message")
        self.message.setWordWrap(True)

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

        panel_layout.addWidget(self.message)
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

        self.input.setFocus()

    # --- input -------------------------------------------------------------
    def submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.message.setText(self.process_input(text))

    def process_input(self, text: str) -> str:
        """Handle a line of user input. Extend this to build your pet's brain."""
        return f"You said: {text}"

    # --- internals ---------------------------------------------------------
    def _on_media_error(self, *_args) -> None:
        self.message.setText(f"Could not play {VIDEO.name}: {self.player.errorString()}")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self.player.stop()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Capri")
    window = Tamagotchi()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
