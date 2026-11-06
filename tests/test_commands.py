from __future__ import annotations

import unittest

from capri.commands import register_default_commands
from capri.commands.registry import CommandRegistry, switch_layout


class TestCommands(unittest.TestCase):
    def test_switch_layout(self) -> None:
        self.assertEqual(switch_layout("ghbdtn"), "привет")
        self.assertEqual(switch_layout("руддщ"), "hello")

    def test_registry_registration_and_match(self) -> None:
        registry = CommandRegistry()
        register_default_commands(registry)
        self.assertGreater(len(registry.commands), 0)
        match = registry.match("пауза")
        self.assertIsNotNone(match)
        if match:
            cmd, arg = match
            self.assertEqual(cmd.name, "пауза")
