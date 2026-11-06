from __future__ import annotations

import unittest

from capri.integrations.system_control import (
    lock_commands,
    power_commands,
)


class TestIntegrations(unittest.TestCase):
    def test_system_control_command_definitions(self) -> None:
        lock_cmds = lock_commands()
        self.assertIsInstance(lock_cmds, list)
        self.assertGreater(len(lock_cmds), 0)

        for action in ("poweroff", "suspend", "reboot"):
            cmds = power_commands(action)
            self.assertIsInstance(cmds, list)
            self.assertGreater(len(cmds), 0)
