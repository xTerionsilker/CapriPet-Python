from __future__ import annotations

import unittest

from capri.integrations.system_control import (
    lock_commands,
    power_commands,
)
from capri.integrations.system_power_hook import (
    PBT_APMSUSPEND,
    WM_ENDSESSION,
    WM_POWERBROADCAST,
    WM_QUERYENDSESSION,
    WM_WTSSESSION_CHANGE,
    WTS_SESSION_LOCK,
    WTS_SESSION_UNLOCK,
    SystemEventHook,
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

    def test_system_power_hook_dispatch(self) -> None:
        events: list[str] = []

        hook = SystemEventHook(
            on_suspend=lambda: events.append("suspend"),
            on_resume=lambda: events.append("resume"),
            on_shutdown=lambda: events.append("shutdown"),
            on_lock=lambda: events.append("lock"),
            on_unlock=lambda: events.append("unlock"),
        )

        self.assertTrue(hook.handle_windows_message(WM_POWERBROADCAST, PBT_APMSUSPEND, 0))
        self.assertEqual(events, ["suspend"])

        self.assertTrue(hook.handle_windows_message(WM_QUERYENDSESSION, 0, 0))
        self.assertEqual(events, ["suspend", "shutdown"])

        self.assertTrue(hook.handle_windows_message(WM_ENDSESSION, 1, 0))
        self.assertEqual(events, ["suspend", "shutdown", "shutdown"])

        self.assertTrue(hook.handle_windows_message(WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK, 0))
        self.assertEqual(events, ["suspend", "shutdown", "shutdown", "lock"])

        self.assertTrue(hook.handle_windows_message(WM_WTSSESSION_CHANGE, WTS_SESSION_UNLOCK, 0))
        self.assertEqual(events, ["suspend", "shutdown", "shutdown", "lock", "unlock"])

        self.assertFalse(hook.handle_windows_message(0x1234, 0, 0))
