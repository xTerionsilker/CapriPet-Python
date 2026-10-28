from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QTimer, Signal

from ..effects.session_animations import SESSION_ACTION_LEAD_MS
from ..integrations import ollama, spotify, web_search
from ..integrations.screen_lock import lock_commands, run_lock
from ..integrations.system_power import power_commands, run_power

OLLAMA_HISTORY_MESSAGES = 12


class ActionBridge(QObject):
    """Мост для выполнения длительных и системных действий (Ollama, Spotify, Power, Lock)."""

    speech_requested = Signal(str)
    session_animation_requested = Signal(str)
    ollama_started = Signal()
    ollama_finished = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock_pending: list[list[str]] | None = None
        self._power_pending: list[list[str]] | None = None

        self._ollama_history: list[dict[str, str]] = []
        self._ollama_pending: str = ""
        self._ollama_busy: bool = False

    # --- Ollama ---

    def ask_ollama(self, prompt: str) -> str:
        prompt = prompt.strip()
        if not prompt:
            return "Что спросить у локальной модели?"
        if self._ollama_busy:
            return "Я всё ещё жду ответ от модели."
        history = list(self._ollama_history)
        self._ollama_pending = prompt
        self._ollama_busy = True
        self.ollama_started.emit()
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
            self._on_ollama_failed(str(error))
            return
        except Exception:
            self._on_ollama_failed("Локальная модель не ответила.")
            return
        self._on_ollama_reply(answer)

    def _on_ollama_reply(self, answer: str) -> None:
        prompt = self._ollama_pending
        self._finish_ollama()
        if prompt:
            self._ollama_history.append({"role": "user", "content": prompt})
            self._ollama_history.append(
                {"role": "assistant", "content": answer}
            )
            del self._ollama_history[:-OLLAMA_HISTORY_MESSAGES]
        self.speech_requested.emit(answer)

    def _on_ollama_failed(self, message: str) -> None:
        self._finish_ollama()
        self.speech_requested.emit(message)

    def _finish_ollama(self) -> None:
        self._ollama_busy = False
        self._ollama_pending = ""
        self.ollama_finished.emit()

    # --- Spotify ---

    def spotify_play(self, query: str) -> str:
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
        self.speech_requested.emit(message)

    def spotify_pause(self) -> str:
        return spotify.pause()

    def spotify_resume(self) -> str:
        return spotify.resume()

    def spotify_next(self) -> str:
        return spotify.next_track()

    def spotify_previous(self) -> str:
        return spotify.previous_track()

    # --- Screen Lock ---

    def lock_screen(self) -> str:
        commands = lock_commands()
        if not commands:
            return "Не удалось найти способ заблокировать экран."
        self._lock_pending = commands
        self.session_animation_requested.emit("lock")
        QTimer.singleShot(SESSION_ACTION_LEAD_MS, self._perform_lock)
        return "Блокирую экран."

    def _perform_lock(self) -> None:
        commands = self._lock_pending
        if not commands:
            return
        self._lock_pending = None
        if not run_lock(commands):
            self.speech_requested.emit("Не удалось заблокировать экран.")

    # --- System Power ---

    def power_off(self) -> str:
        return self._queue_power("poweroff", "Выключаю ПК.")

    def suspend(self) -> str:
        return self._queue_power("suspend", "Ухожу в спящий режим.")

    def reboot(self) -> str:
        return self._queue_power("reboot", "Перезагружаю ПК.")

    # --- Web Search ---

    def search_google(self, query: str) -> str:
        return web_search.search_google(query)

    def search_youtube(self, query: str) -> str:
        return web_search.search_youtube(query)

    def _queue_power(self, action: str, message: str) -> str:
        commands = power_commands(action)
        if not commands:
            return "Не удалось найти способ выполнить это действие."
        self._power_pending = commands
        animation_action = "power_off" if action == "poweroff" else action
        self.session_animation_requested.emit(animation_action)
        QTimer.singleShot(SESSION_ACTION_LEAD_MS, self._perform_power)
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
            self.speech_requested.emit("Не удалось выполнить действие.")
