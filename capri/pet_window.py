"""Главное окно Capri: зацикленное видео питомца и ввод команд.

Окно собирает интерфейс и связывает части приложения воедино, а всё, что
можно описать отдельно, вынесено в соседние модули:

* ``capri.command_catalog`` — встроенные команды и их обработчики;
* ``capri.input_flow``     — разбор ввода и подтверждение «да» / «нет»;
* ``capri.wake_word``       — ключевое слово «Капри» и окно ожидания;
* ``capri.screen_lock``     — блокировка экрана;
* ``capri.glitch``, ``capri.static_noise``, ``capri.voice``, ``capri.speech``
  — эффекты и служебные окна.
"""

from __future__ import annotations

import getpass
import random
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl, Signal
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
    from capri.command_catalog import Handlers, register_commands
    from capri.commands import CommandRegistry
    from capri.glitch import GlitchManager
    from capri.input_flow import InputFlow
    from capri.screen_lock import lock_commands, run_lock
    from capri.speech import SpeechWindow, show_text
    from capri.static_noise import StaticNoise
    from capri.theme import APP_STYLE
    from capri.voice import VoiceInput
    from capri.wake_word import (
        VOICE_COMMAND_WINDOW_MS,
        VOICE_LISTENING_STATUS,
        VOICE_WAITING_STATUS,
        command_after_trigger,
    )
    import capri.spotify as spotify
else:
    from .command_catalog import Handlers, register_commands
    from .commands import CommandRegistry
    from .glitch import GlitchManager
    from .input_flow import InputFlow
    from .screen_lock import lock_commands, run_lock
    from .speech import SpeechWindow, show_text
    from .static_noise import StaticNoise
    from .theme import APP_STYLE
    from .voice import VoiceInput
    from .wake_word import (
        VOICE_COMMAND_WINDOW_MS,
        VOICE_LISTENING_STATUS,
        VOICE_WAITING_STATUS,
        command_after_trigger,
    )
    from . import spotify

ROOT = Path(__file__).resolve().parent.parent
FACES = ROOT / "faces"

# Приветственное видео — один раз при запуске.
START_VIDEO = FACES / "start.mp4"
# Основное видео — бесконечный цикл во время работы.
VIDEO = FACES / "capri.mp4"
# Прощальное видео — один раз при выходе из программы.
END_VIDEO = FACES / "end.mp4"

# Все видео приложения (для проверки, что хоть что-то есть).
VIDEOS = (START_VIDEO, VIDEO, END_VIDEO)

# Служебные дорожки: звук к приветствию и прощанию.
VOICES = ROOT / "voices"
START_SOUND = VOICES / "start.mp3"
END_SOUND = VOICES / "end.mp3"

PLAYBACK_RATE = 1.5
# Скорость служебных роликов: приветствия и прощания.
SERVICE_PLAYBACK_RATE = 2.0

# Фазы жизненного цикла плеера: приветствие → цикл → прощание.
PHASE_START = "start"
PHASE_MAIN = "main"
PHASE_END = "end"
PHASE_CLOSED = "closed"

STARTUP_LINES = (
    "Молодец, {user}",
    "зови меня просто Capri!!!",
    "...",
)

# Прощание в облачке при выходе из программы.
GOODBYE_LINE = "пока пока чумба"

# Задержка перед блокировкой экрана, чтобы пользователь успел прочитать
# ответ Capri.
LOCK_DELAY_MS = 800


class CapriWindow(QWidget):
    """Окно питомца. Напишите или скажите что-нибудь — Capri ответит."""

    spotify_reply = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CAPRI")
        # Окно фиксированного размера: его нельзя растянуть, развернуть
        # на весь экран или открыть в полноэкранном режиме.
        self.setFixedSize(800, 540)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setStyleSheet(APP_STYLE)

        self._speech: SpeechWindow | None = None
        self._greeted = False
        self._lock_pending: list[list[str]] | None = None
        self._voice_armed_until = 0.0
        # Текущая фаза плеера: приветствие, цикл, прощание или закрытие.
        self._phase = PHASE_MAIN
        self._closing = False
        # Досмотрены ли части прощания (ролик и дорожка).
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

        self.input.setFocus()

    # --- сборка интерфейса -------------------------------------------------
    def _build_video(self) -> None:
        """Видео питомца: приветствие, бесконечный цикл, прощание."""
        self.video = QVideoWidget(self)
        self.video.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.video.setMinimumSize(320, 180)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.6)
        # Все ролики воспроизводятся без звука.
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
        """Отдельный плеер для дорожек из ``voices/``.

        В отличие от видео, озвучка не глушится: приветствие звучит
        при запуске, прощание — при выходе из программы.
        """
        self.sound = QMediaPlayer(self)
        self.sound_audio = QAudioOutput(self)
        self.sound_audio.setVolume(0.6)
        self.sound.setAudioOutput(self.sound_audio)
        self.sound.errorOccurred.connect(self._on_sound_error)
        self.sound.mediaStatusChanged.connect(self._on_sound_status)

        if START_SOUND.is_file():
            self._play_sound(START_SOUND)

    def _play_sound(self, path: Path) -> None:
        """Проиграть дорожку из ``voices/`` ровно один раз."""
        self.sound.setLoops(QMediaPlayer.Loops.Once)
        self.sound.setSource(QUrl.fromLocalFile(str(path)))
        self.sound.play()

    def _play_source(
        self, path: Path, loops: QMediaPlayer.Loops, rate: float
    ) -> None:
        """Переключить плеер на ``path`` и запустить воспроизведение."""
        self.player.setLoops(loops)
        self.player.setPlaybackRate(rate)
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def _play_intro(self) -> None:
        """Приветственное видео — ровно один раз при запуске."""
        self._phase = PHASE_START
        self.video.show()
        self._play_source(
            START_VIDEO, QMediaPlayer.Loops.Once, SERVICE_PLAYBACK_RATE
        )

    def _play_main(self) -> None:
        """Основное видео — бесконечный цикл во время работы."""
        self._phase = PHASE_MAIN
        if not VIDEO.is_file():
            self.video.hide()
            return
        self.video.show()
        self._play_source(VIDEO, QMediaPlayer.Loops.Infinite, PLAYBACK_RATE)

    def _play_outro(self) -> None:
        """Прощание: ролик и дорожка — каждый ровно один раз."""
        have_video = END_VIDEO.is_file()
        have_sound = END_SOUND.is_file()
        # Чего нет, то считаем уже досмотренным.
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
        """Закрыться, когда досмотрены и ролик, и дорожка прощания."""
        if self._phase != PHASE_END:
            return
        if self._outro_video_done and self._outro_sound_done:
            self._finish_close()

    def _build_controls(self) -> None:
        """Нижняя панель: статус, поле ввода и кнопки."""
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
        """Горячие клавиши окна."""
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Ctrl+Space"), self, self._toggle_voice)

    def _build_effects(self) -> None:
        """Глитч-оверлей, управляющий фоновым шумом."""
        self._static = StaticNoise(self)
        self._glitches = GlitchManager(self)
        self._glitches.amplitude_changed.connect(self._static.set_amplitude)

    def _build_voice(self) -> None:
        """Голосовой ввод и окно ожидания команды после «Капри»."""
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

    def _register_commands(self) -> None:
        """Подключить встроенные команды к обработчикам этого окна."""
        register_commands(
            self.commands,
            Handlers(
                toggle_glitches=self._toggle_glitches,
                toggle_noise=self._toggle_noise,
                toggle_voice=self._toggle_voice,
                search_google=self._search_google,
                search_youtube=self._search_youtube,
                spotify_play=self._spotify_play,
                spotify_pause=self._spotify_pause,
                spotify_resume=self._spotify_resume,
                spotify_next=self._spotify_next,
                spotify_previous=self._spotify_previous,
                lock_screen=self._lock_screen,
            ),
        )

    # --- события Qt --------------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        if not self._greeted:
            self._greeted = True
            QTimer.singleShot(600, self._greet)

    def changeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().changeEvent(event)
        # Оконный менеджер может развернуть окно двойным кликом по заголовку
        # или горячей клавишей — возвращаем фиксированный размер.
        if event.type() == QEvent.Type.WindowStateChange and (
            self.isMaximized() or self.isFullScreen()
        ):
            QTimer.singleShot(0, self.showNormal)

    # --- ввод --------------------------------------------------------------
    def submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.speak(self.process_input(text))

    def process_input(self, text: str) -> str:
        """Обработать строку пользователя. Здесь можно расширять «мозг» Capri.

        По умолчанию текст уходит в ``capri.input_flow``: сначала проверяется
        ответ на предложенную команду, затем точные совпадения и подсказка.
        """
        return self._flow.handle(text)

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
        после ключевого слова (см. ``capri.wake_word``).
        """
        command = command_after_trigger(text)
        if command is not None:
            return command
        # Пока ждём «да» / «нет», отвечать можно без ключевого слова.
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

    # --- эффекты -----------------------------------------------------------
    def _toggle_glitches(self) -> str:
        enabled = self._glitches.toggle()
        return "Глитчи включены." if enabled else "Глитчи выключены."

    def _toggle_noise(self) -> str:
        enabled = self._static.toggle()
        return "Шум включён." if enabled else "Шум выключен."

    # --- поиск в интернете -------------------------------------------------
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

    # --- Spotify -----------------------------------------------------------
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

    # --- блокировка экрана -------------------------------------------------
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

    # --- внутреннее --------------------------------------------------------
    def _greet(self) -> None:
        if self._speech is not None:  # пользователь уже получил ответ
            return
        if self._closing:  # окно уже прощается — не мешаем
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
        # Сбой служебного ролика не должен ни зависнуть запуск,
        # ни помешать выйти из программы.
        if self._phase == PHASE_START:
            QTimer.singleShot(0, self._play_main)
        elif self._phase == PHASE_END:
            self._outro_video_done = True
            QTimer.singleShot(0, self._maybe_finish_outro)

    def _on_media_status(self, status) -> None:
        """Перевести плеер на следующую фазу по мере окончания ролика."""
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if self._phase == PHASE_START:
            self._play_main()
        elif self._phase == PHASE_END:
            self._outro_video_done = True
            self._maybe_finish_outro()

    def _on_sound_error(self, *_args) -> None:
        """Сбой дорожки не должен ни зависнуть запуск, ни задержать выход."""
        if self._phase == PHASE_END:
            self._outro_sound_done = True
            QTimer.singleShot(0, self._maybe_finish_outro)

    def _on_sound_status(self, status) -> None:
        """Пометить дорожку прощания досмотренной по её окончании."""
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if self._phase == PHASE_END:
            self._outro_sound_done = True
            self._maybe_finish_outro()

    def _finish_close(self) -> None:
        """Прощание досмотрено и дослушано — завершить закрытие окна."""
        self._phase = PHASE_CLOSED
        self.player.stop()
        self.sound.stop()
        # Облачко больше не нужно: убираем его вместе с окном, чтобы
        # приложение не доживало само по себе.
        if self._speech is not None:
            self._speech.close()
        QTimer.singleShot(0, self.close)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        # Второй проход: служебные окна уже остановлены, прощание
        # досмотрено и дослушано — закрываемось и даём приложению
        # завершиться.
        if self._closing or self._phase == PHASE_CLOSED:
            self.player.stop()
            self.sound.stop()
            super().closeEvent(event)
            return
        # Первый проход: откладываем закрытие, чтобы попрощаться —
        # показать faces/end.mp4 и проиграть voices/end.mp3.
        self._closing = True
        event.ignore()
        self._voice.cancel()
        self._static.stop()
        self._glitches.stop()
        self.speak(GOODBYE_LINE)
        self._play_outro()


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from main import main

    raise SystemExit(main())
