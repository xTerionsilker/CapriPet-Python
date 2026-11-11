"""Интеграция с Discord Rich Presence (RPC).

Обеспечивает подключение к локальному клиенту Discord через IPC,
периодическую синхронизацию статуса питомца, отображение текущей
голосовой команды и информации о воспроизводимом треке в Spotify.
"""

from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Callable
from typing import Any

try:
    from pypresence import Presence
except ImportError:
    Presence = None  # type: ignore[misc,assignment]

from PySide6.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)

DEFAULT_CLIENT_ID = "1567968896277938266"
GITHUB_REPO_URL = "https://github.com/xTerionsilker/CapriPet-Python"


class DiscordRpcManager(QObject):
    """Менеджер интеграции с Discord Rich Presence.

    Управляет жизненным циклом подключения к Discord, периодически
    обновляет статус присутствия (presence) питомца с помощью QTimer,
    отображает название текущего трека и предоставляет интерактивные
    кнопки со ссылкой на проект.
    """

    def __init__(
        self,
        client_id: str = DEFAULT_CLIENT_ID,
        track_provider: Callable[[], str] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._client_id: str = client_id
        self._track_provider: Callable[[], str] | None = track_provider
        self._rpc: Any = None
        self._connected: bool = False
        self._start_time: int = int(time.time())
        self._current_state: str = "ASR: Vosk | IDLE"
        self._current_details: str = "Команда: нет"
        self._current_large_image: str = "capri_avatar"
        self._current_large_text: str = "CapriPet // Rogue AI"
        self._current_small_image: str | None = "net_pulse"
        self._current_small_text: str | None = "ONLINE"
        self._buttons: list[dict[str, str]] = [
            {"label": "Скачать проект", "url": GITHUB_REPO_URL}
        ]

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(5_000)
        self._poll_timer.timeout.connect(self._sync_presence)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        self.connect_rpc()
        self._poll_timer.start()

    def stop(self) -> None:
        self._poll_timer.stop()
        self.close_rpc()

    def connect_rpc(self) -> bool:
        if self._connected:
            return True
        if Presence is None:
            return False
        try:
            self._rpc = Presence(self._client_id)
            self._rpc.connect()
            self._connected = True
            self._push_presence()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("Discord RPC connection failed: %s", exc)
            self._connected = False
            self._rpc = None
            return False

    def close_rpc(self) -> None:
        if self._rpc is not None and self._connected:
            with contextlib.suppress(Exception):
                self._rpc.close()
        self._connected = False
        self._rpc = None

    def update_presence(
        self,
        state: str | None = None,
        details: str | None = None,
        large_image: str | None = None,
        large_text: str | None = None,
        small_image: str | None = None,
        small_text: str | None = None,
    ) -> None:
        if state is not None:
            self._current_state = state
        if details is not None:
            self._current_details = details
        if large_image is not None:
            self._current_large_image = large_image
        if large_text is not None:
            self._current_large_text = large_text
        if small_image is not None:
            self._current_small_image = small_image
        if small_text is not None:
            self._current_small_text = small_text

        self._push_presence()

    def _sync_presence(self) -> None:
        if not self._connected:
            self.connect_rpc()
        else:
            self._push_presence()

    def _resolve_track_info(self) -> str | None:
        if self._track_provider is None:
            return None
        try:
            raw = self._track_provider()
            if not raw:
                return None
            prefix = "Сейчас играет: "
            if raw.startswith(prefix):
                return raw[len(prefix) :].strip()
            return None
        except Exception as exc:  # noqa: BLE001
            logger.debug("Spotify track provider error: %s", exc)
            return None

    def _push_presence(self) -> None:
        if not self._connected or self._rpc is None:
            return
        track_info = self._resolve_track_info()
        details_text = self._current_details
        state_text = self._current_state
        if track_info:
            details_text = f"♫ {track_info}"
            if len(details_text) > 120:
                details_text = details_text[:119] + "…"
            state_text = f"{self._current_details} | {self._current_state}"
            if len(state_text) > 120:
                state_text = state_text[:119] + "…"
        try:
            self._rpc.update(
                state=state_text,
                details=details_text,
                large_image=self._current_large_image,
                large_text=self._current_large_text,
                small_image=self._current_small_image,
                small_text=self._current_small_text,
                start=self._start_time,
                buttons=self._buttons,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Discord RPC update error: %s", exc)
            self._connected = False
            self._rpc = None
