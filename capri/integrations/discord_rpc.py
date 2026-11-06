from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)

DEFAULT_CLIENT_ID = "1567968896277938266"
GITHUB_REPO_URL = "https://github.com/xTerionsilker/CapriPet-Python"

class DiscordRpcManager(QObject):

    def __init__(
        self,
        client_id: str = DEFAULT_CLIENT_ID,
        track_provider: Optional[Callable[[], str]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._client_id: str = client_id
        self._track_provider: Optional[Callable[[], str]] = track_provider
        self._rpc: Optional[object] = None
        self._connected: bool = False
        self._start_time: int = int(time.time())
        self._current_state: str = "ASR: Vosk | IDLE"
        self._current_details: str = "Команда: нет"
        self._current_large_image: str = "capri_avatar"
        self._current_large_text: str = "CapriPet // Rogue AI"
        self._current_small_image: Optional[str] = "net_pulse"
        self._current_small_text: Optional[str] = "ONLINE"
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
        try:
            from pypresence import Presence
            self._rpc = Presence(self._client_id)
            self._rpc.connect()
            self._connected = True
            self._push_presence()
            return True
        except Exception as exc:
            logger.debug("Discord RPC connection failed: %s", exc)
            self._connected = False
            self._rpc = None
            return False

    def close_rpc(self) -> None:
        if self._rpc is not None and self._connected:
            try:
                self._rpc.close()
            except Exception:
                pass
        self._connected = False
        self._rpc = None

    def update_presence(
        self,
        state: Optional[str] = None,
        details: Optional[str] = None,
        large_image: Optional[str] = None,
        large_text: Optional[str] = None,
        small_image: Optional[str] = None,
        small_text: Optional[str] = None,
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
    def _resolve_track_info(self) -> Optional[str]:
        if self._track_provider is None:
            return None
        try:
            raw = self._track_provider()
            if not raw:
                return None
            prefix = "Сейчас играет: "
            if raw.startswith(prefix):
                return raw[len(prefix):].strip()
            return None
        except Exception as exc:
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
        except Exception as exc:
            logger.debug("Discord RPC update error: %s", exc)
            self._connected = False
            self._rpc = None
