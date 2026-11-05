from __future__ import annotations

import logging
import time
from typing import Optional

from PySide6.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)

DEFAULT_CLIENT_ID = "1567968896277938266"

class DiscordRpcManager(QObject):

    def __init__(
        self,
        client_id: str = DEFAULT_CLIENT_ID,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._client_id: str = client_id
        self._rpc: Optional[object] = None
        self._connected: bool = False
        self._start_time: int = int(time.time())
        self._current_state: str = "STATUS // SECURE"
        self._current_details: str = "BLACKWALL BREACH DETECTED"
        self._current_large_image: str = "capri_avatar"
        self._current_large_text: str = "CapriPet // Rogue AI"
        self._current_small_image: Optional[str] = "net_pulse"
        self._current_small_text: Optional[str] = "ONLINE"

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(15_000)
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
    def _push_presence(self) -> None:
        if not self._connected or self._rpc is None:
            return
        try:
            self._rpc.update(
                state=self._current_state,
                details=self._current_details,
                large_image=self._current_large_image,
                large_text=self._current_large_text,
                small_image=self._current_small_image,
                small_text=self._current_small_text,
                start=self._start_time,
            )
        except Exception as exc:
            logger.debug("Discord RPC update error: %s", exc)
            self._connected = False
            self._rpc = None
