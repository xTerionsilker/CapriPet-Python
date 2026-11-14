"""Unit tests for DialogueManager and dialogue style presets."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from capri.core.dialogue_manager import (
    DEFAULT_STYLE_ID,
    DialogueManager,
    DialoguePreset,
    get_dialogue_manager,
)


class TestDialogueManager(unittest.TestCase):
    """Test suite for DialogueManager preset loading, fallback and resolution."""

    def setUp(self) -> None:
        self.dm = DialogueManager()

    def test_presets_loaded(self) -> None:
        styles = self.dm.list_styles()
        style_ids = [s.id for s in styles]
        self.assertIn("arasaka_engram", style_ids)
        self.assertIn("partner_duo", style_ids)

    def test_switch_style(self) -> None:
        self.assertTrue(self.dm.set_style("partner_duo", persist=False))
        self.assertEqual(self.dm.current_style, "partner_duo")

        reminders = self.dm.get_reminder_phrases()
        self.assertTrue(
            any("напарник" in r.lower() or "партнёр" in r.lower() for r in reminders)
        )

        self.assertTrue(self.dm.set_style("arasaka_engram", persist=False))
        self.assertEqual(self.dm.current_style, "arasaka_engram")
        engram_reminders = self.dm.get_reminder_phrases()
        self.assertTrue(
            any("хост" in r.lower() or "мясной" in r.lower() for r in engram_reminders)
        )

    def test_unknown_style_fallback(self) -> None:
        self.assertFalse(self.dm.set_style("non_existent_style_xyz", persist=False))
        self.assertEqual(self.dm.current_style, DEFAULT_STYLE_ID)

    def test_process_reactions_resolution(self) -> None:
        self.dm.set_style("arasaka_engram", persist=False)
        dev_reactions = self.dm.get_process_reactions("dev")
        self.assertGreater(len(dev_reactions), 0)

        self.dm.set_style("partner_duo", persist=False)
        partner_dev = self.dm.get_process_reactions("dev")
        self.assertGreater(len(partner_dev), 0)
        self.assertNotEqual(dev_reactions, partner_dev)

    def test_shredder_formatting(self) -> None:
        self.dm.set_style("arasaka_engram", persist=False)
        phrase = self.dm.get_shredder_phrase("tiny", bytes=100, name="secret.txt")
        self.assertIn("100", phrase)
        self.assertIn("secret.txt", phrase)

        self.dm.set_style("partner_duo", persist=False)
        p_phrase = self.dm.get_shredder_phrase("tiny", bytes=100, name="secret.txt")
        self.assertIn("100", p_phrase)
        self.assertIn("secret.txt", p_phrase)
        self.assertNotEqual(phrase, p_phrase)

    def test_dodge_phrases(self) -> None:
        self.dm.set_style("arasaka_engram", persist=False)
        dodge_engram = self.dm.get_dodge_phrases()
        self.assertGreater(len(dodge_engram), 0)

        self.dm.set_style("partner_duo", persist=False)
        dodge_partner = self.dm.get_dodge_phrases()
        self.assertGreater(len(dodge_partner), 0)
        self.assertNotEqual(dodge_engram, dodge_partner)

    def test_command_phrase(self) -> None:
        self.dm.set_style("arasaka_engram", persist=False)
        cmd_p = self.dm.get_command_phrase("app_prompt", count=3)
        self.assertIn("3", cmd_p)

        self.dm.set_style("partner_duo", persist=False)
        p_cmd_p = self.dm.get_command_phrase("app_prompt", count=3)
        self.assertIn("3", p_cmd_p)
        self.assertIn("напарник", p_cmd_p)

    def test_json_files_schema_validity(self) -> None:
        dialogues_dir = Path(__file__).resolve().parents[1] / "assets" / "dialogues"
        self.assertTrue(dialogues_dir.is_dir())
        for file in dialogues_dir.glob("*.json"):
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
            preset = DialoguePreset.model_validate(data)
            self.assertTrue(bool(preset.meta.id))
            self.assertTrue(bool(preset.inactivity.reminders))
            self.assertIn("dev", preset.process_reactions)

    def test_singleton(self) -> None:
        dm1 = get_dialogue_manager()
        dm2 = get_dialogue_manager()
        self.assertIs(dm1, dm2)


if __name__ == "__main__":
    unittest.main()
