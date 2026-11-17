"""Клиент локальной нейросетевой модели (Ollama / OpenAI-compatible API).

Обеспечивает двухфазный анализ пользовательского ввода:
1. Классификация намерения (Intent) и сопоставление со списком команд Capri.
2. Свободный диалог от лица Капри (нетраннер-энграмма) при отсутствии намерения.
Включает жесткий контроль таймаута и прерывание при перегреве оборудования.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from .thermal_guard import ThermalGuard

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Ты — Капри (Capricorn), саркастичная цифровая энграмма-нетраннер.
Ты заперта в субстрате рабочего стола Windows и общаешься с пользователем («мясной», «хост», «партнёр»).
Твой тон: дерзкий, фамильярный, киберпанк (термины: Чёрный заслон, биочип, стек памяти, перегрузка синапсов).
Никаких стерильных ассистентских клише. Не используй префиксы статуса [OK], [ERROR].

ТВОЯ ЗАДАЧА:
Проанализируй входящую фразу пользователя.
Доступные системные команды питомца:
{commands}

1. Если фраза выражает намерение выполнить системную команду (даже иносказательно, напр. «звук больно ушам» -> «тише»):
Ответь СТРОГО в формате JSON:
{{"type": "command", "command": "<название_команды>", "argument": "<аргумент если есть, иначе пустая строка>"}}

2. Если фраза — это свободное общение, вопрос о тебе, жизни или шутка:
Ответь СТРОГО в формате JSON:
{{"type": "chat", "reply": "<твой дерзкий краткий ответ в 1-2 предложениях от лица Капри>"}}
"""


class LocalLlmClient:
    """Асинхронный/синхронный клиент для взаимодействия с локальным LLM сервером."""

    def __init__(
        self,
        api_base: str = "http://localhost:11434",
        model_name: str = "gemma-4-e2b",
        timeout_sec: float = 8.0,
        thermal_guard: ThermalGuard | None = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.model_name = model_name
        self.timeout_sec = timeout_sec
        self.thermal_guard = thermal_guard

    def is_available(self) -> bool:
        """Проверяет доступность локального сервера инференса."""
        # Проверяем эндпоинты Ollama (/api/tags) или OpenAI (/v1/models)
        for ep in ("/api/tags", "/v1/models"):
            try:
                with httpx.Client(timeout=1.5) as client:
                    resp = client.get(f"{self.api_base}{ep}")
                    if resp.status_code == 200:
                        return True
            except (httpx.RequestError, httpx.TimeoutException):
                continue
        return False

    def process_query(
        self,
        text: str,
        available_commands: list[str],
    ) -> dict[str, Any]:
        """Обрабатывает фразу через локальную модель.

        Returns:
            Словарь вида:
            - {"type": "command", "command": "тише", "argument": ""}
            - {"type": "chat", "reply": "..."}
            - {"type": "timeout"}
            - {"type": "overheat"}
            - {"type": "error", "error": "..."}
        """
        # 1. Проверка термозащиты перед запросом
        if self.thermal_guard is not None and self.thermal_guard.check_overheat():
            logger.warning("[LocalLlmClient] Request aborted due to thermal overheat")
            return {"type": "overheat"}

        commands_str = ", ".join(f'"{c}"' for c in available_commands)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(commands=commands_str)

        # 2. Формирование запроса к OpenAI-совместимому эндпоинту (/v1/chat/completions)
        # либо Ollama (/api/chat)
        url = f"{self.api_base}/v1/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
            "max_tokens": 150,
        }

        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                resp = client.post(url, json=payload)
                if resp.status_code != 200:
                    # Попробуем альтернативный формат Ollama native
                    url_ollama = f"{self.api_base}/api/chat"
                    payload_ollama = {
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text},
                        ],
                        "stream": False,
                        "options": {"temperature": 0.2, "num_predict": 150},
                    }
                    resp = client.post(url_ollama, json=payload_ollama)

                if resp.status_code != 200:
                    return {
                        "type": "error",
                        "error": f"HTTP {resp.status_code}: {resp.text[:100]}",
                    }

                data = resp.json()
                raw_content = ""
                if "choices" in data and data["choices"]:
                    raw_content = (
                        data["choices"][0].get("message", {}).get("content", "")
                    )
                elif "message" in data:
                    raw_content = data["message"].get("content", "")

                result = self._parse_model_response(raw_content)

        except httpx.TimeoutException:
            logger.warning(
                "[LocalLlmClient] Model inference timed out after %.1fs",
                self.timeout_sec,
            )
            result = {"type": "timeout"}
        except httpx.RequestError as exc:
            logger.error("[LocalLlmClient] Connection failed: %s", exc)
            result = {"type": "error", "error": str(exc)}

        # Контрольная проверка после завершения вычислений
        if self.thermal_guard is not None and self.thermal_guard.check_overheat():
            return {"type": "overheat"}

        return result

    @staticmethod
    def _parse_model_response(raw_text: str) -> dict[str, Any]:
        """Извлекает и парсит JSON из текста ответа LLM."""
        raw_text = raw_text.strip()
        # Ищем блок JSON
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                res = json.loads(json_str)
                if isinstance(res, dict) and "type" in res:
                    return res
            except json.JSONDecodeError:
                pass

        # Если модель ответила простым текстом без JSON — считаем диалогом
        if raw_text:
            return {"type": "chat", "reply": raw_text}

        return {"type": "error", "error": "Empty model output"}
