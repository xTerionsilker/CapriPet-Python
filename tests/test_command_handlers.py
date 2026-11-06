from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from capri.commands import register_default_commands
from capri.commands.base import CommandContext
from capri.commands.handlers import format_duration
from capri.commands.registry import CommandRegistry


class TestCommandHandlers(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CommandRegistry()
        register_default_commands(self.registry)
        self.context = CommandContext(
            speak=MagicMock(),
            trigger_glitches=MagicMock(return_value="glitch"),
            toggle_voice=MagicMock(return_value="voice_toggled"),
            locate_mouse=MagicMock(return_value="mouse_located"),
            set_pose=MagicMock(),
            get_config=MagicMock(return_value=50),
            set_config=MagicMock(),
            debug_info=MagicMock(return_value={"version": "1.0"}),
        )

    def test_format_duration(self) -> None:
        self.assertEqual(format_duration(None), "неизвестно")
        self.assertEqual(format_duration(45), "45 с")
        self.assertEqual(format_duration(125), "2 мин 05 с")
        self.assertEqual(format_duration(3665), "1 ч 01 мин")

    def test_glitch_command_execution(self) -> None:
        match = self.registry.match("глитч")
        self.assertIsNotNone(match)
        if match:
            cmd, arg = match
            result = cmd.execute(self.context, arg)
            self.assertEqual(result, "glitch")
            self.context.trigger_glitches.assert_called_once()

    def test_unknown_command_fallback(self) -> None:
        match = self.registry.match("абсолютно_неизвестная_фраза_xyz")
        self.assertIsNone(match)
