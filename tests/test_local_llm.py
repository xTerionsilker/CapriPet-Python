"""Тесты для клиента локальной LLM модели (LocalLlmClient)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import httpx

from capri.integrations.local_llm import LocalLlmClient
from capri.integrations.thermal_guard import ThermalGuard


class TestLocalLlmClient(unittest.TestCase):
    """Набор тестов для LocalLlmClient."""

    def test_process_query_command_json(self) -> None:
        client = LocalLlmClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '```json\n{"type": "command", "command": "тише", "argument": "20"}\n```'
                    }
                }
            ]
        }

        with patch("httpx.Client.post", return_value=mock_resp):
            res = client.process_query("звук больно ушам", ["тише", "громче"])
            self.assertEqual(res["type"], "command")
            self.assertEqual(res["command"], "тише")
            self.assertEqual(res["argument"], "20")

    def test_process_query_chat_response(self) -> None:
        client = LocalLlmClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"type": "chat", "reply": "Опять ты лезешь в мой субстрат, мясной?"}'
                    }
                }
            ]
        }

        with patch("httpx.Client.post", return_value=mock_resp):
            res = client.process_query("привет, кто ты?", ["тише", "громче"])
            self.assertEqual(res["type"], "chat")
            self.assertIn("мясной", res["reply"])

    def test_process_query_timeout(self) -> None:
        client = LocalLlmClient(timeout_sec=2.0)
        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Timeout")):
            res = client.process_query("тяжелый запрос", ["тише"])
            self.assertEqual(res["type"], "timeout")

    def test_process_query_overheat_abort(self) -> None:
        guard = MagicMock(spec=ThermalGuard)
        guard.check_overheat.return_value = True

        client = LocalLlmClient(thermal_guard=guard)
        res = client.process_query("любой запрос", ["тише"])
        self.assertEqual(res["type"], "overheat")


if __name__ == "__main__":
    unittest.main()
