#!/usr/bin/env python3
"""A tiny Tamagotchi: a looping character video plus a text input.

The window shows capri.mp4 on repeat. Type a command below the video and the
pet reacts. Processing happens in ``Tamagotchi.process_command`` — replace or
extend that method to plug in your own logic (an LLM, a state machine, ...).

Commands: feed, play, sleep, status, help.
Quit with Ctrl+Q.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
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
    background: #12101a;
    color: #f2e9ff;
    font-family: "DejaVu Sans", sans-serif;
    font-size: 14px;
}
QVideoWidget { background: #000; }
#panel {
    background: #1b1725;
    border-top: 1px solid #2e2740;
}
#stats { color: #9d92b8; font-size: 12px; }
#message { font-size: 15px; }
#panel QLabel { background: transparent; }
QLineEdit {
    background: #241f33;
    border: 1px solid #3a3152;
    border-radius: 12px;
    padding: 9px 14px;
    selection-background-color: #6d4aff;
}
QLineEdit:focus { border-color: #8b6cff; }
QPushButton {
    background: #6d4aff;
    border: none;
    border-radius: 12px;
    padding: 9px 20px;
    font-weight: 600;
}
QPushButton:hover { background: #7d5eff; }
QPushButton:pressed { background: #5a3be0; }
"""


class Pet:
    """Minimal pet state. All values are 0-100."""

    def __init__(self) -> None:
        self.hunger = 50  # 100 = starving
        self.happiness = 50
        self.energy = 50

    def clamp(self) -> None:
        self.hunger = max(0, min(100, self.hunger))
        self.happiness = max(0, min(100, self.happiness))
        self.energy = max(0, min(100, self.energy))

    def idle_tick(self) -> None:
        """Called periodically so the pet slowly changes on its own."""
        self.hunger += 2
        self.happiness -= 1
        self.energy -= 1
        self.clamp()

    def summary(self) -> str:
        return (
            f"Hunger {self.hunger}  ·  Mood {self.happiness}  ·  "
            f"Energy {self.energy}"
        )


class Tamagotchi(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Capri")
        self.resize(800, 570)
        self.setMinimumSize(480, 400)
        self.setStyleSheet(STYLE)

        self.pet = Pet()

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

        self.stats = QLabel(self.pet.summary(), panel)
        self.stats.setObjectName("stats")

        self.message = QLabel(
            "Capri looks at you expectantly. Try “help”." if VIDEO.is_file()
            else f"Video not found: {VIDEO.name}",
            panel,
        )
        self.message.setObjectName("message")
        self.message.setWordWrap(True)

        self.input = QLineEdit(panel)
        self.input.setPlaceholderText("Say something to Capri…")
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(self.submit)

        send = QPushButton("Send", panel)
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.clicked.connect(self.submit)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.input, 1)
        row.addWidget(send)

        panel_layout.addWidget(self.stats)
        panel_layout.addWidget(self.message)
        panel_layout.addLayout(row)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.video, 1)
        root.addWidget(panel)

        # Slow passive change, once every 15 seconds.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(15_000)

        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

        self.input.setFocus()

    # --- input -------------------------------------------------------------
    def submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.message.setText(self.process_command(text))
        self.stats.setText(self.pet.summary())

    def process_command(self, text: str) -> str:
        """Turn user input into a reply. Extend this to build your pet's brain."""
        command = text.lower().strip(" .!?")

        if command in {"help", "commands", "?"}:
            return "Commands: feed, play, sleep, status."

        if command == "feed":
            if self.pet.hunger <= 5:
                return "Capri is already full and politely refuses."
            self.pet.hunger -= 30
            self.pet.happiness += 5
            self.pet.energy += 5
            self.pet.clamp()
            return "Capri munches happily. *crunch crunch*"

        if command == "play":
            if self.pet.energy < 15:
                return "Capri is too tired to play. Maybe let it sleep?"
            self.pet.happiness += 20
            self.pet.energy -= 15
            self.pet.hunger += 5
            self.pet.clamp()
            return "You play together. Capri bounces with joy!"

        if command == "sleep":
            self.pet.energy += 30
            self.pet.hunger += 5
            self.pet.clamp()
            return "Capri curls up and naps for a moment. Zzz…"

        if command == "status":
            return self.pet.summary()

        return (
            f"Capri tilts its head at “{text}”. "
            "It only understands: feed, play, sleep, status, help."
        )

    # --- internals ---------------------------------------------------------
    def _tick(self) -> None:
        self.pet.idle_tick()
        self.stats.setText(self.pet.summary())

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
