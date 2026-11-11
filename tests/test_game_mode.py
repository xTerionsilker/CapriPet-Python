"""Тесты детектора полноэкранного игрового режима и исключения развёрнутых окон."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from capri.integrations.game_mode import (
    QUNS_BUSY,
    QUNS_RUNNING_D3D_FULL_SCREEN,
    WS_CAPTION,
    WS_MAXIMIZE,
    WS_POPUP,
    GameModeDetector,
    is_window_fullscreen_on_screen,
)


class TestGameModeDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not QApplication.instance():
            cls._app = QApplication([])

    def test_windowed_with_caption_is_not_fullscreen(self) -> None:
        """Окно со стандартным заголовком (WS_CAPTION) не считается полноэкранным."""
        mock_user32 = MagicMock()
        mock_user32.IsWindow.return_value = True
        mock_user32.IsIconic.return_value = False
        mock_user32.GetDesktopWindow.return_value = 100
        mock_user32.GetShellWindow.return_value = 101
        mock_user32.IsZoomed.return_value = False
        mock_user32.GetWindowLongW.return_value = WS_CAPTION

        with patch("ctypes.windll.user32", mock_user32):
            self.assertFalse(is_window_fullscreen_on_screen(444))

    def test_maximized_window_is_not_fullscreen(self) -> None:
        """Развёрнутое окно (IsZoomed=True / WS_MAXIMIZE) не должно считаться полноэкранным."""
        mock_user32 = MagicMock()
        mock_user32.IsWindow.return_value = True
        mock_user32.IsIconic.return_value = False
        mock_user32.GetDesktopWindow.return_value = 100
        mock_user32.GetShellWindow.return_value = 101

        # Окно развёрнуто (IsZoomed = True)
        mock_user32.IsZoomed.return_value = True
        mock_user32.GetWindowLongW.return_value = WS_POPUP | WS_MAXIMIZE

        with patch("ctypes.windll.user32", mock_user32):
            self.assertFalse(is_window_fullscreen_on_screen(555))

    def test_borderless_fullscreen_game_is_detected(self) -> None:
        """Игра в Borderless Fullscreen без WS_MAXIMIZE и покрывающая монитор должна детектироваться."""
        mock_user32 = MagicMock()
        mock_user32.IsWindow.return_value = True
        mock_user32.IsIconic.return_value = False
        mock_user32.GetDesktopWindow.return_value = 100
        mock_user32.GetShellWindow.return_value = 101
        mock_user32.IsZoomed.return_value = False
        mock_user32.GetWindowLongW.return_value = WS_POPUP

        def fake_get_window_rect(hwnd, rect_ptr):
            rect = getattr(rect_ptr, "_obj", getattr(rect_ptr, "contents", None))
            if rect is not None:
                rect.left = 0
                rect.top = 0
                rect.right = 1920
                rect.bottom = 1080
            return True

        def fake_get_monitor_info(h_mon, mi_ptr):
            mi = getattr(mi_ptr, "_obj", getattr(mi_ptr, "contents", None))
            if mi is not None:
                mi.rcMonitor.left = 0
                mi.rcMonitor.top = 0
                mi.rcMonitor.right = 1920
                mi.rcMonitor.bottom = 1080
                mi.rcWork.left = 0
                mi.rcWork.top = 0
                mi.rcWork.right = 1920
                mi.rcWork.bottom = 1040
            return True

        mock_user32.GetWindowRect.side_effect = fake_get_window_rect
        mock_user32.MonitorFromWindow.return_value = 999
        mock_user32.GetMonitorInfoW.side_effect = fake_get_monitor_info

        with patch("ctypes.windll.user32", mock_user32):
            self.assertTrue(is_window_fullscreen_on_screen(777))

    def test_discord_maximized_not_game_foreground(self) -> None:
        """Переключение в развёрнутый Discord не должно активировать игровой режим."""
        detector = GameModeDetector(suppression_enabled=False)

        mock_user32 = MagicMock()
        mock_user32.GetForegroundWindow.return_value = 12345
        mock_user32.IsWindow.return_value = True
        mock_user32.IsIconic.return_value = False
        mock_user32.GetDesktopWindow.return_value = 100
        mock_user32.GetShellWindow.return_value = 101
        mock_user32.IsZoomed.return_value = True
        mock_user32.GetWindowLongW.return_value = WS_POPUP | WS_MAXIMIZE

        with (
            patch("ctypes.windll.user32", mock_user32),
            patch(
                "capri.integrations.game_mode.query_user_notification_state",
                return_value=QUNS_BUSY,
            ),
            patch(
                "capri.integrations.game_mode.get_foreground_process_info",
                return_value=(1234, "discord.exe"),
            ),
        ):
            self.assertFalse(detector._is_game_foreground())

    def test_whitelist_overrides_d3d_state(self) -> None:
        """Приложение в whitelist не должно активировать игровой режим даже при D3D статусе."""
        detector = GameModeDetector(
            suppression_enabled=False, whitelist=["discord.exe"]
        )

        mock_user32 = MagicMock()
        mock_user32.GetForegroundWindow.return_value = 12345

        with (
            patch("ctypes.windll.user32", mock_user32),
            patch(
                "capri.integrations.game_mode.query_user_notification_state",
                return_value=QUNS_RUNNING_D3D_FULL_SCREEN,
            ),
            patch(
                "capri.integrations.game_mode.get_foreground_process_info",
                return_value=(1234, "discord.exe"),
            ),
        ):
            self.assertFalse(detector._is_game_foreground())


if __name__ == "__main__":
    unittest.main()
