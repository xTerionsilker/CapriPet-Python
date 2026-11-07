"""Перехват низкоуровневых системных событий питания и сессий Windows.

Обрабатывает оконные сообщения Windows для обнаружения перехода системы
в спящий режим, возобновления работы, завершения сеанса, а также
блокировки и разблокировки рабочей станции.
"""

from __future__ import annotations

import ctypes
from collections.abc import Callable

WM_POWERBROADCAST = 0x0218
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012

WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016

WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
NOTIFY_FOR_THIS_SESSION = 0


class SystemEventHook:
    """Обработчик системных событий питания и блокировки экрана Windows.

    Регистрирует уведомления терминальной сессии (WTS) для заданного HWND
    и маршрутизирует оконные сообщения (WM_POWERBROADCAST, WM_ENDSESSION,
    WM_WTSSESSION_CHANGE) в соответствующие функции обратного вызова (колбэки).
    """

    def __init__(
        self,
        on_suspend: Callable[[], None] | None = None,
        on_resume: Callable[[], None] | None = None,
        on_shutdown: Callable[[], None] | None = None,
        on_lock: Callable[[], None] | None = None,
        on_unlock: Callable[[], None] | None = None,
    ) -> None:
        self._on_suspend = on_suspend
        self._on_resume = on_resume
        self._on_shutdown = on_shutdown
        self._on_lock = on_lock
        self._on_unlock = on_unlock
        self._registered_hwnd: int | None = None

    def register_session_notification(self, hwnd: int) -> bool:
        if hwnd <= 0:
            return False
        try:
            wtsapi32 = ctypes.windll.wtsapi32
            res = bool(
                wtsapi32.WTSRegisterSessionNotification(
                    hwnd, NOTIFY_FOR_THIS_SESSION
                )
            )
            if res:
                self._registered_hwnd = hwnd
            return res
        except Exception:
            return False

    def unregister_session_notification(self) -> bool:
        if not self._registered_hwnd:
            return False
        try:
            wtsapi32 = ctypes.windll.wtsapi32
            res = bool(
                wtsapi32.WTSUnRegisterSessionNotification(
                    self._registered_hwnd
                )
            )
            self._registered_hwnd = None
            return res
        except Exception:
            self._registered_hwnd = None
            return False

    def handle_windows_message(
        self, msg_id: int, wparam: int, _lparam: int
    ) -> bool:
        if msg_id == WM_POWERBROADCAST:
            if wparam == PBT_APMSUSPEND:
                if self._on_suspend is not None:
                    self._on_suspend()
                return True
            if wparam in (PBT_APMRESUMESUSPEND, PBT_APMRESUMEAUTOMATIC):
                if self._on_resume is not None:
                    self._on_resume()
                return True
        elif msg_id in (WM_QUERYENDSESSION, WM_ENDSESSION):
            if self._on_shutdown is not None:
                self._on_shutdown()
            return True
        elif msg_id == WM_WTSSESSION_CHANGE:
            if wparam == WTS_SESSION_LOCK:
                if self._on_lock is not None:
                    self._on_lock()
                return True
            if wparam == WTS_SESSION_UNLOCK:
                if self._on_unlock is not None:
                    self._on_unlock()
                return True
        return False
