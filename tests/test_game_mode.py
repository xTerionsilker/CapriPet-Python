"""Тесты детектора полноэкранного игрового режима и исключения развёрнутых окон."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import win32con
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
        with (
            patch("win32gui.IsWindow", return_value=True),
            patch("win32gui.IsIconic", return_value=False),
            patch("win32gui.GetDesktopWindow", return_value=100),
            patch(
                "win32gui.GetWindowPlacement",
                return_value=(0, win32con.SW_SHOWNORMAL, (0, 0), (0, 0), (0, 0, 100, 100)),
            ),
            patch("win32gui.GetWindowLong", return_value=WS_CAPTION),
        ):
            self.assertFalse(is_window_fullscreen_on_screen(444))

    def test_maximized_window_is_not_fullscreen(self) -> None:
        """Развёрнутое окно (IsZoomed=True / WS_MAXIMIZE) не должно считаться полноэкранным."""
        with (
            patch("win32gui.IsWindow", return_value=True),
            patch("win32gui.IsIconic", return_value=False),
            patch("win32gui.GetDesktopWindow", return_value=100),
            patch(
                "win32gui.GetWindowPlacement",
                return_value=(0, win32con.SW_SHOWMAXIMIZED, (0, 0), (0, 0), (0, 0, 100, 100)),
            ),
            patch("win32gui.GetWindowLong", return_value=WS_POPUP | WS_MAXIMIZE),
        ):
            self.assertFalse(is_window_fullscreen_on_screen(555))

    def test_borderless_fullscreen_game_is_detected(self) -> None:
        """Игра в Borderless Fullscreen без WS_MAXIMIZE и покрывающая монитор должна детектироваться."""
        with (
            patch("win32gui.IsWindow", return_value=True),
            patch("win32gui.IsIconic", return_value=False),
            patch("win32gui.GetDesktopWindow", return_value=100),
            patch(
                "win32gui.GetWindowPlacement",
                return_value=(0, win32con.SW_SHOWNORMAL, (0, 0), (0, 0), (0, 0, 1920, 1080)),
            ),
            patch("win32gui.GetWindowLong", return_value=WS_POPUP),
            patch("win32gui.GetWindowRect", return_value=(0, 0, 1920, 1080)),
            patch("win32api.MonitorFromWindow", return_value=999),
            patch(
                "win32api.GetMonitorInfo",
                return_value={"Monitor": (0, 0, 1920, 1080)},
            ),
        ):
            self.assertTrue(is_window_fullscreen_on_screen(777))

    def test_discord_maximized_not_game_foreground(self) -> None:
        """Переключение в развёрнутый Discord не должно активировать игровой режим."""
        detector = GameModeDetector(suppression_enabled=False)

        with (
            patch("win32gui.GetForegroundWindow", return_value=12345),
            patch("win32gui.IsWindow", return_value=True),
            patch(
                "win32gui.GetWindowPlacement",
                return_value=(0, win32con.SW_SHOWMAXIMIZED, (0, 0), (0, 0), (0, 0, 100, 100)),
            ),
            patch("win32gui.GetWindowLong", return_value=WS_POPUP | WS_MAXIMIZE),
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

        with (
            patch("win32gui.GetForegroundWindow", return_value=12345),
            patch("win32gui.IsWindow", return_value=True),
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
