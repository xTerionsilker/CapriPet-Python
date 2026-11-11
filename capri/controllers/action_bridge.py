"""Мост между пользовательскими командами и фоновыми системными операциями."""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QTimer, Signal

from ..effects.session_animations import SESSION_ACTION_LEAD_MS
from ..integrations import (
    app_launcher,
    process_manager,
    spotify,
    system_cleaner,
    web_search,
)
from ..integrations.system_control import (
    lock_commands,
    power_commands,
    run_lock,
    run_power,
)


class ActionBridge(QObject):
    """Мост для выполнения длительных и системных действий (Spotify, Power, Lock)."""

    speech_requested = Signal(str)
    session_animation_requested = Signal(str)
    youtube_results_ready = Signal(list)
    launch_app_results_ready = Signal(list)
    kill_app_results_ready = Signal(list)
    update_check_finished = Signal(str, object, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock_pending: list[list[str]] | None = None
        self._power_pending: list[list[str]] | None = None

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
        except Exception:  # noqa: BLE001
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

    def power_off(self) -> str:
        return self._queue_power("poweroff", "Выключаю ПК.")

    def suspend(self) -> str:
        return self._queue_power("suspend", "Ухожу в спящий режим.")

    def reboot(self) -> str:
        return self._queue_power("reboot", "Перезагружаю ПК.")

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
            return (
                "Какое приложение запустить? Скажи: «запусти <название>»."
            )
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
        return web_search.open_update_page()

    def check_updates(self) -> str:
        threading.Thread(
            target=self._check_updates_worker,
            name="capri-update-check",
            daemon=True,
        ).start()
        return "Проверяю наличие обновлений…"

    def clean_system(self) -> str:
        threading.Thread(
            target=self._clean_system_worker,
            name="capri-system-clean",
            daemon=True,
        ).start()
        return "Начинаю безопасную очистку мусора и временных файлов…"

    def _clean_system_worker(self) -> None:
        try:
            res = system_cleaner.perform_system_cleanup()
            freed_str = system_cleaner.format_bytes(res.bytes_freed)
            if res.files_deleted == 0 and res.bytes_freed == 0:
                msg = "Система чиста: временных файлов и мусора в корзине не обнаружено."
            else:
                msg = f"Очистка завершена: удалено {res.files_deleted} объектов, освобождено {freed_str}."
        except Exception:  # noqa: BLE001
            msg = "Произошла ошибка при очистке системы."
        self.speech_requested.emit(msg)

    def _check_updates_worker(self) -> None:
        local_dt = web_search.read_local_version_datetime()
        remote_dt = web_search.fetch_remote_version_datetime()
        if remote_dt is None:
            self.speech_requested.emit(
                "Не удалось получить данные об обновлении с GitHub."
            )
            return
        if local_dt is None:
            self.speech_requested.emit(
                "Локальный файл версий не найден или повреждён."
            )
            return

        local_str = web_search.format_version_datetime(local_dt)
        remote_str = web_search.format_version_datetime(remote_dt)

        if remote_dt > local_dt:
            self.update_check_finished.emit(
                "update_available", local_str, remote_str
            )
        elif remote_dt == local_dt:
            self.speech_requested.emit(
                "Установлена актуальная версия. Обновлять нечего."
            )
        else:
            self.speech_requested.emit(
                f"Твоя версия ({local_str}) новее репозитория ({remote_str}). Ты из будущего!"
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
        parent = self.parent()
        if parent is not None and hasattr(parent, "window"):
            window = parent.window
            if window is not None and hasattr(window, "close"):
                QTimer.singleShot(200, window.close)

    def _power_worker(self, commands: list[list[str]]) -> None:
        if not run_power(commands):
            self.speech_requested.emit("Не удалось выполнить действие.")
