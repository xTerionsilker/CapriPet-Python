"""Обнаружение полноэкранных игр и мультимедийных приложений в Windows.

Модуль определяет работу пользователя в полноэкранном или игровом режиме
через Windows Shell API (SHQueryUserNotificationState) и анализ геометрии
активных окон для автоматического подавления анимаций и голосовых реплик.
"""

from __future__ import annotations

import ctypes
import logging

import psutil
import win32api
import win32con
import win32gui
import win32process
from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)

QUNS_NOT_PRESENT = 1
QUNS_BUSY = 2
QUNS_RUNNING_D3D_FULL_SCREEN = 3
QUNS_PRESENTATION_MODE = 4
QUNS_ACCEPTS_NOTIFICATIONS = 5
QUNS_QUIET_TIME = 6
QUNS_APP = 7

WS_POPUP = win32con.WS_POPUP
WS_MAXIMIZE = win32con.WS_MAXIMIZE
WS_CAPTION = win32con.WS_CAPTION
GWL_STYLE = win32con.GWL_STYLE


def query_user_notification_state() -> int:
    try:
        shell32 = ctypes.windll.shell32
        state = ctypes.c_int()
        if shell32.SHQueryUserNotificationState(ctypes.byref(state)) == 0:
            return int(state.value)
    except (OSError, AttributeError):
        pass
    return QUNS_NOT_PRESENT


def get_foreground_process_info(hwnd: int) -> tuple[int, str]:
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid:
            proc = psutil.Process(pid)
            return pid, proc.name().lower()
    except (psutil.Error, Exception):
        pass
    return 0, ""


def is_window_fullscreen_on_screen(hwnd: int) -> bool:
    try:
        if not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):
            return False

        if hwnd == win32gui.GetDesktopWindow():
            return False

        try:
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMAXIMIZED:
                return False
        except Exception:
            pass

        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        if (style & win32con.WS_MAXIMIZE) != 0 or (style & win32con.WS_CAPTION) == win32con.WS_CAPTION:
            return False

        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect

        h_mon = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
        if not h_mon:
            return False

        mi = win32api.GetMonitorInfo(h_mon)
        m_left, m_top, m_right, m_bottom = mi["Monitor"]
        width = right - left
        height = bottom - top
        m_width = m_right - m_left
        m_height = m_bottom - m_top

        is_matching_monitor = (
            left <= m_left
            and top <= m_top
            and right >= m_right
            and bottom >= m_bottom
        )
        return (
            is_matching_monitor and width >= m_width and height >= m_height
        )
    except Exception:
        return False


class GameModeDetector(QObject):
    """Детектор активности полноэкранных игр и презентаций.

    Отслеживает состояние окна на переднем плане и статус уведомлений системы.
    Поддерживает белые и черные списки процессов, а также таймер задержки
    (cooldown) для сглаживания кратковременных переключений между окнами.
    При смене режима генерирует сигнал `game_mode_changed`.
    """

    game_mode_changed = Signal(bool)

    def __init__(
        self,
        suppression_enabled: bool = True,
        cooldown_seconds: float = 3.0,
        whitelist: list[str] | None = None,
        blacklist: list[str] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._enabled = suppression_enabled
        self._cooldown_seconds = max(0.5, float(cooldown_seconds))
        self._whitelist = [w.lower() for w in (whitelist or [])]
        self._blacklist = [b.lower() for b in (blacklist or [])]

        self._in_game = False
        self._raw_detected = False

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._check_state)

        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setSingleShot(True)
        self._cooldown_timer.timeout.connect(self._on_cooldown_expired)

        if self._enabled:
            self._poll_timer.start()

    @property
    def is_game_active(self) -> bool:
        return self._in_game

    @property
    def suppression_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            if not self._poll_timer.isActive():
                self._poll_timer.start()
            self._check_state()
        else:
            self._poll_timer.stop()
            self._cooldown_timer.stop()
            if self._in_game:
                self._in_game = False
                self.game_mode_changed.emit(False)

    def set_lists(
        self, whitelist: list[str], blacklist: list[str]
    ) -> None:
        self._whitelist = [w.lower() for w in whitelist]
        self._blacklist = [b.lower() for b in blacklist]

    def _is_game_foreground(self) -> bool:
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or not win32gui.IsWindow(hwnd):
                return False

            _, proc_name = get_foreground_process_info(hwnd)
            if proc_name:
                if proc_name in self._whitelist:
                    return False
                if proc_name in self._blacklist:
                    return True

            # Развёрнутые на весь экран окна обычных приложений (Discord, браузер) не являются играми
            if win32gui.IsZoomed(hwnd):
                return False

            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if (style & win32con.WS_MAXIMIZE) != 0:
                return False

            user_state = query_user_notification_state()
            if user_state in (
                QUNS_RUNNING_D3D_FULL_SCREEN,
                QUNS_PRESENTATION_MODE,
            ):
                return True

            if is_window_fullscreen_on_screen(hwnd):
                if (style & win32con.WS_POPUP) != 0 or user_state == QUNS_BUSY:
                    return True

            return False
        except Exception:
            return False

    def _check_state(self) -> None:
        if not self._enabled:
            return

        currently_game = self._is_game_foreground()
        if currently_game:
            self._raw_detected = True
            self._cooldown_timer.stop()
            if not self._in_game:
                self._in_game = True
                self.game_mode_changed.emit(True)
        else:
            if self._in_game and self._raw_detected:
                self._raw_detected = False
                self._cooldown_timer.start(
                    int(self._cooldown_seconds * 1000)
                )

    def _on_cooldown_expired(self) -> None:
        if not self._raw_detected and self._in_game:
            self._in_game = False
            self.game_mode_changed.emit(False)
