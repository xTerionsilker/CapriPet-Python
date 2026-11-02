from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QTimer, Signal

from ..effects.session_animations import SESSION_ACTION_LEAD_MS
from ..integrations import ai_client, app_launcher, process_manager, spotify, updater, web_search
from ..integrations.screen_lock import lock_commands, run_lock
from ..integrations.system_power import power_commands, run_power

AI_HISTORY_MESSAGES = 12


class ActionBridge(QObject):
    """Мост для выполнения длительных и системных действий (AI, Spotify, Power, Lock)."""

    speech_requested = Signal(str)
    session_animation_requested = Signal(str)
    ai_started = Signal()
    ai_finished = Signal()
    youtube_results_ready = Signal(list)
    launch_app_results_ready = Signal(list)
    kill_app_results_ready = Signal(list)
    update_check_finished = Signal(str, object, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock_pending: list[list[str]] | None = None
        self._power_pending: list[list[str]] | None = None

        self._ai_history: list[dict[str, str]] = []
        self._ai_pending: str = ""
        self._ai_busy: bool = False

    # --- AI Integration ---

    def ask_ai(self, prompt: str) -> str:
        prompt = prompt.strip()
        if not prompt:
            return "Что спросить у нейросети?"
        if self._ai_busy:
            return "Я всё ещё жду ответ от модели."
        history = list(self._ai_history)
        self._ai_pending = prompt
        self._ai_busy = True
        self.ai_started.emit()
        threading.Thread(
            target=self._ask_ai_worker,
            args=(prompt, history),
            name="capri-ai",
            daemon=True,
        ).start()
        return "Думаю…"

    def _ask_ai_worker(
        self, prompt: str, history: list[dict[str, str]]
    ) -> None:
        try:
            answer = ai_client.ask(prompt, history=history)
        except ai_client.AIError as error:
            self._on_ai_failed(str(error))
            return
        except Exception:
            self._on_ai_failed("Нейросеть не ответила.")
            return
        self._on_ai_reply(answer)

    def _on_ai_reply(self, answer: str) -> None:
        prompt = self._ai_pending
        self._finish_ai()
        if prompt:
            self._ai_history.append({"role": "user", "content": prompt})
            self._ai_history.append(
                {"role": "assistant", "content": answer}
            )
            del self._ai_history[:-AI_HISTORY_MESSAGES]
        self.speech_requested.emit(answer)

    def _on_ai_failed(self, message: str) -> None:
        self._finish_ai()
        self.speech_requested.emit(message)

    def _finish_ai(self) -> None:
        self._ai_busy = False
        self._ai_pending = ""
        self.ai_finished.emit()

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

    def spotify_current_track(self) -> str:
        return spotify.current_track()

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
        trimmed = query.strip()
        if not trimmed:
            return "Что искать на YouTube? Скажи: «ютуб <запрос>»."
        web_search.search_youtube(trimmed)
        threading.Thread(
            target=self._fetch_youtube_worker,
            args=(trimmed,),
            name="capri-youtube-fetch",
            daemon=True,
        ).start()
        return f"Ищу на YouTube: {trimmed}"

    def _fetch_youtube_worker(self, query: str) -> None:
        videos = web_search.fetch_youtube_top_videos(query, limit=5)
        if videos:
            self.youtube_results_ready.emit(videos)

    def launch_app(self, query: str) -> str:
        trimmed = query.strip()
        if not trimmed:
            return "Какое приложение запустить? Скажи: «запусти <название>»."
        threading.Thread(
            target=self._find_apps_worker,
            args=(trimmed,),
            name="capri-app-find",
            daemon=True,
        ).start()
        return f"Ищу приложение: {trimmed}"

    def _find_apps_worker(self, query: str) -> None:
        apps = app_launcher.find_matching_applications(query, limit=5)
        self.launch_app_results_ready.emit(apps)

    def kill_app(self, query: str) -> str:
        trimmed = query.strip()
        if not trimmed:
            return "Какой процесс убить? Скажи: «убей <название>»."
        threading.Thread(
            target=self._find_processes_worker,
            args=(trimmed,),
            name="capri-process-find",
            daemon=True,
        ).start()
        return f"Ищу процессы: {trimmed}"

    def _find_processes_worker(self, query: str) -> None:
        procs = process_manager.find_matching_processes(query, limit=5)
        self.kill_app_results_ready.emit(procs)

    def open_update_page(self) -> str:
        return updater.open_update_page()

    def check_updates(self) -> str:
        threading.Thread(
            target=self._check_updates_worker,
            name="capri-update-check",
            daemon=True,
        ).start()
        return "Проверяю наличие обновлений…"

    def _check_updates_worker(self) -> None:
        local_date = updater.read_local_version_date()
        remote_date = updater.fetch_remote_version_date()
        if remote_date is None:
            self.speech_requested.emit(
                "Не удалось получить данные об обновлении с GitHub."
            )
            return
        if local_date is None:
            self.speech_requested.emit(
                "Локальный файл версий не найден или повреждён."
            )
            return

        if remote_date > local_date:
            self.update_check_finished.emit("update_available", local_date, remote_date)
        elif remote_date == local_date:
            self.speech_requested.emit("Установлена актуальная версия. Обновлять нечего.")
        else:
            self.speech_requested.emit(
                f"Твоя версия ({local_date}) новее репозитория ({remote_date}). Ты из будущего!"
            )

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
