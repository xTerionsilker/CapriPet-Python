"""Тесты для интеграции LLM и конвейера обработки команд в PetOrchestrator."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from capri.commands import BaseCommand, CommandContext
from capri.commands.registry import CommandRegistry
from capri.controllers.orchestrator import PetOrchestrator
from capri.core.settings import get_config_value, set_config_value


class DummyWindow(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.is_closing = False
        self.speak = MagicMock()
        self.get_designated_screen = MagicMock(return_value=None)
        self.toggle_glitches = MagicMock()
        self.find_mouse_position = MagicMock()
        self.set_pose = MagicMock()
        self.open_console = MagicMock()
        self.actions = MagicMock()
        self.actions.spotify_current_track = MagicMock(return_value=None)

    def isVisible(self) -> bool:
        return True


class DummyVolumeDownCommand(BaseCommand):
    name = "тише"
    aliases = ("потише",)
    description = "Сделать тише"
    takes_argument = True

    def execute(self, context: CommandContext, argument: str = "") -> str:
        return f"Громкость уменьшена: arg={argument}"


class TestOrchestratorLlmIntegration(unittest.TestCase):
    """Тестирование двухфазного роутинга и LLM в оркестраторе."""

    @classmethod
    def setUpClass(cls) -> None:
        if QApplication.instance() is None:
            cls._app = QApplication([])
        else:
            cls._app = QApplication.instance()

    def setUp(self) -> None:
        self.mock_window = DummyWindow()

        self.orchestrator = PetOrchestrator(self.mock_window)
        self.orchestrator.commands = CommandRegistry()
        ctx = CommandContext(
            speak=self.mock_window.speak,
            trigger_glitches=self.mock_window.toggle_glitches,
            toggle_voice=MagicMock(),
            locate_mouse=self.mock_window.find_mouse_position,
            set_pose=self.mock_window.set_pose,
            get_config=get_config_value,
            set_config=set_config_value,
        )
        self.orchestrator.commands.context = ctx
        self.orchestrator.commands.register(DummyVolumeDownCommand())
        self.orchestrator.flow._registry = self.orchestrator.commands

    def test_llm_disabled_by_default(self) -> None:
        self.assertFalse(get_config_value("llm.enabled", False))
        # При неизвестной фразе и выключенной LLM возвращается «Ты сказал:...»
        self.orchestrator.handle_command("звук больно ушам")
        self.mock_window.speak.assert_called_with("Ты сказал: звук больно ушам")

    def test_llm_intent_command_execution(self) -> None:
        set_config_value("llm.enabled", True)
        try:
            with patch.object(
                self.orchestrator.llm_client,
                "process_query",
                return_value={"type": "command", "command": "тише", "argument": "10"},
            ):
                self.orchestrator.handle_command("звук больно ушам")
                # Должен быть вызван обработчик команды «тише»
                self.mock_window.speak.assert_called_with("Громкость уменьшена: arg=10")
        finally:
            set_config_value("llm.enabled", False)

    def test_llm_chat_reply(self) -> None:
        set_config_value("llm.enabled", True)
        try:
            with patch.object(
                self.orchestrator.llm_client,
                "process_query",
                return_value={"type": "chat", "reply": "Отвали, мясной, я компилирую шейдер."},
            ):
                self.orchestrator.handle_command("кто создал вселенную?")
                self.mock_window.speak.assert_called_with(
                    "Отвали, мясной, я компилирую шейдер."
                )
        finally:
            set_config_value("llm.enabled", False)

    def test_llm_overheat_emergency_shutoff(self) -> None:
        set_config_value("llm.enabled", True)
        try:
            with patch.object(
                self.orchestrator.thermal_guard,
                "check_overheat",
                return_value=True,
            ):
                self.orchestrator.handle_command("любая фраза")
                # Проверяем, что LLM отключена в конфиге
                self.assertFalse(get_config_value("llm.enabled", False))
                # И выдано предупреждение о перегреве
                args, _ = self.mock_window.speak.call_args
                self.assertIn("перегре", args[0])
        finally:
            set_config_value("llm.enabled", False)


if __name__ == "__main__":
    unittest.main()
