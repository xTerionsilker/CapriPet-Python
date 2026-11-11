"""Tests for decomposed command domains, audio DSP generators, and UI delegates."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from capri.audio.sfx_generators import (
    DEFAULT_SAMPLE_RATE,
    _generate_chirp_wav,
    _generate_swoosh_wav,
)
from capri.commands import (
    DEFAULT_COMMAND_CLASSES,
    create_default_registry,
)
from capri.commands.apps import LaunchAppCommand
from capri.commands.debug import (
    DebugCommand,
)
from capri.commands.handlers import (
    SpotifyPlayCommand as HandlersSpotifyPlay,
)
from capri.commands.handlers import (
    VolumeUpCommand as HandlersVolumeUp,
)
from capri.commands.media import SpotifyPlayCommand
from capri.commands.system import LockScreenCommand
from capri.commands.volume import VolumeUpCommand
from capri.commands.web import GoogleSearchCommand
from capri.ui.reminder_dialog import ReminderRangeDialog
from capri.ui.shredder_drop_handler import ShredderDropHandler
from capri.ui.tray_manager import CAPRI_ICON, TrayManager


class TestCommandsModular(unittest.TestCase):
    """Тесты модульности командной подсистемы и новых делегатов."""

    def test_default_registry_has_all_26_commands(self) -> None:
        registry = create_default_registry()
        self.assertEqual(len(registry.commands), 26)
        self.assertEqual(len(DEFAULT_COMMAND_CLASSES), 26)

    def test_domain_command_instantiation(self) -> None:
        cmd_app = LaunchAppCommand()
        cmd_debug = DebugCommand()
        cmd_media = SpotifyPlayCommand()
        cmd_sys = LockScreenCommand()
        cmd_vol = VolumeUpCommand()
        cmd_web = GoogleSearchCommand()

        self.assertEqual(cmd_app.name, "запусти")
        self.assertEqual(cmd_debug.name, "дебаг")
        self.assertEqual(cmd_media.name, "спотифай")
        self.assertEqual(cmd_sys.name, "блокировка")
        self.assertEqual(cmd_vol.name, "Громче")
        self.assertEqual(cmd_web.name, "гугл")

    def test_handlers_facade_backward_compatibility(self) -> None:
        self.assertIs(SpotifyPlayCommand, HandlersSpotifyPlay)
        self.assertIs(VolumeUpCommand, HandlersVolumeUp)

    def test_audio_dsp_generation_pure_python(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            temp_path = Path(td) / "test_swoosh.wav"
            _generate_swoosh_wav(temp_path, sample_rate=DEFAULT_SAMPLE_RATE, duration=0.05)
            self.assertTrue(temp_path.exists())
            self.assertGreater(temp_path.stat().st_size, 44)

            chirp_path = Path(td) / "test_chirp.wav"
            _generate_chirp_wav(chirp_path, sample_rate=DEFAULT_SAMPLE_RATE, duration=0.05)
            self.assertTrue(chirp_path.exists())

    def test_tray_and_dialog_classes_available(self) -> None:
        self.assertTrue(hasattr(TrayManager, "init_tray"))
        self.assertTrue(hasattr(ReminderRangeDialog, "paintEvent"))
        self.assertTrue(hasattr(ShredderDropHandler, "handle_drop"))
        self.assertTrue(CAPRI_ICON.name.endswith(".png"))


if __name__ == "__main__":
    unittest.main()
