from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget

ROOT = Path(__file__).resolve().parent.parent.parent
FACES = ROOT / "faces"

START_VIDEO = FACES / "start.mp4"
MAIN_VIDEO = FACES / "capri.mp4"
END_VIDEO = FACES / "end.mp4"
VIDEOS = (START_VIDEO, MAIN_VIDEO, END_VIDEO)

VOICES = ROOT / "voices"
START_SOUND = VOICES / "start.mp3"
END_SOUND = VOICES / "end.mp3"

PLAYBACK_RATE = 1.5
SERVICE_PLAYBACK_RATE = 2.0

PHASE_START = "start"
PHASE_MAIN = "main"
PHASE_END = "end"
PHASE_CLOSED = "closed"


class MediaController(QObject):
    """Управление воспроизведением видео-фаз питомца и фоновых звуковых эффектов."""

    error_occurred = Signal(str)
    outro_completed = Signal()

    def __init__(self, parent: QWidget, video_widget: QVideoWidget) -> None:
        super().__init__(parent)
        self._parent = parent
        self.video = video_widget

        self._phase = PHASE_MAIN
        self._outro_video_done = True
        self._outro_sound_done = True

        self.player = QMediaPlayer(parent)
        self.audio = QAudioOutput(parent)
        self.audio.setVolume(0.6)
        self.audio.setMuted(True)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.errorOccurred.connect(self._on_media_error)
        self.player.mediaStatusChanged.connect(self._on_media_status)

        self.sound = QMediaPlayer(parent)
        self.sound_audio = QAudioOutput(parent)
        self.sound_audio.setVolume(0.6)
        self.sound.setAudioOutput(self.sound_audio)
        self.sound.errorOccurred.connect(self._on_sound_error)
        self.sound.mediaStatusChanged.connect(self._on_sound_status)

    def set_volume(self, volume: float) -> None:
        """Устанавливает уровень громкости для видео и системных звуков (0.0..1.0)."""
        vol = max(0.0, min(1.0, float(volume)))
        self.audio.setVolume(vol)
        self.sound_audio.setVolume(vol)

    @property
    def phase(self) -> str:
        return self._phase

    @phase.setter
    def phase(self, value: str) -> None:
        self._phase = value

    def start_playback(self) -> None:
        if not any(path.is_file() for path in VIDEOS):
            self.video.hide()
            return
        if START_VIDEO.is_file():
            self.play_intro()
        else:
            self.play_main()

        if START_SOUND.is_file():
            self.play_sound(START_SOUND)

    def play_sound(self, path: Path) -> None:
        self.sound.setLoops(QMediaPlayer.Loops.Once)
        self.sound.setSource(QUrl.fromLocalFile(str(path)))
        self.sound.play()

    def play_source(
        self, path: Path, loops: QMediaPlayer.Loops, rate: float
    ) -> None:
        self.player.setLoops(loops)
        self.player.setPlaybackRate(rate)
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def play_intro(self) -> None:
        self._phase = PHASE_START
        self.video.show()
        self.play_source(
            START_VIDEO, QMediaPlayer.Loops.Once, SERVICE_PLAYBACK_RATE
        )

    def play_main(self) -> None:
        self._phase = PHASE_MAIN
        if not MAIN_VIDEO.is_file():
            self.video.hide()
            return
        self.video.show()
        self.play_source(MAIN_VIDEO, QMediaPlayer.Loops.Infinite, PLAYBACK_RATE)

    def play_outro(self) -> None:
        have_video = END_VIDEO.is_file()
        have_sound = END_SOUND.is_file()
        self._outro_video_done = not have_video
        self._outro_sound_done = not have_sound

        if not have_video and not have_sound:
            self.outro_completed.emit()
            return

        self._phase = PHASE_END
        if have_video:
            self.video.show()
            self.play_source(
                END_VIDEO, QMediaPlayer.Loops.Once, SERVICE_PLAYBACK_RATE
            )
        if have_sound:
            self.play_sound(END_SOUND)
        self._maybe_finish_outro()

    def _maybe_finish_outro(self) -> None:
        if self._phase != PHASE_END:
            return
        if self._outro_video_done and self._outro_sound_done:
            self.outro_completed.emit()

    def stop(self) -> None:
        self._phase = PHASE_CLOSED
        self.player.stop()
        self.sound.stop()

    def _on_media_error(self, *_args) -> None:
        self.error_occurred.emit(self.player.errorString())
        if self._phase == PHASE_START:
            QTimer.singleShot(0, self.play_main)
        elif self._phase == PHASE_END:
            self._outro_video_done = True
            QTimer.singleShot(0, self._maybe_finish_outro)

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if self._phase == PHASE_START:
            self.play_main()
        elif self._phase == PHASE_END:
            self._outro_video_done = True
            self._maybe_finish_outro()

    def _on_sound_error(self, *_args) -> None:
        if self._phase == PHASE_END:
            self._outro_sound_done = True
            QTimer.singleShot(0, self._maybe_finish_outro)

    def _on_sound_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if self._phase == PHASE_END:
            self._outro_sound_done = True
            self._maybe_finish_outro()
