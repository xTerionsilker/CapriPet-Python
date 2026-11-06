from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from capri.integrations.process_manager import (
    _score_candidate,
    get_running_processes,
)


class TestProcessManager(unittest.TestCase):
    def test_score_candidate(self) -> None:
        self.assertEqual(_score_candidate("notepad", "notepad"), 100.0)
        self.assertGreater(_score_candidate("note", "notepad.exe"), 70.0)
        self.assertGreater(_score_candidate("chrome", "chrome.exe"), 80.0)

    @patch("capri.integrations.process_manager.psutil.process_iter")
    def test_get_running_processes(self, mock_iter: MagicMock) -> None:
        mock_proc = MagicMock()
        mock_proc.info = {
            "pid": 1234,
            "name": "discord.exe",
            "cmdline": ["discord.exe", "--start-minimized"],
        }
        mock_iter.return_value = [mock_proc]

        procs = get_running_processes()
        self.assertEqual(len(procs), 1)
        self.assertEqual(procs[0]["pid"], 1234)
        self.assertEqual(procs[0]["name"], "discord.exe")
        self.assertIn("discord.exe", procs[0]["cmd"])
