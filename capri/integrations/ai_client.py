from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from ..core.ai_config import get_ai_config_value, load_ai_config
from ..core.user_agent import get_user_agent

logger = logging.getLogger(__name__)


class AIError(RuntimeError):
    """Базовое исключение для ошибок взаимодействия с AI API."""
    pass


def normalize_endpoint(raw_url: str) -> str:
    """Нормализует URL эндпоинта AI API.

    Если указан базовый путь /v1, автоматически добавляет /chat/completions.
    """
    url = raw_url.strip()
    if not url:
        return "https://api.openai.com/v1/chat/completions"

    if "://" not in url:
        if url.startswith("localhost") or url.startswith("127.0.0.1"):
            url = f"http://{url}"
        else:
            url = f"https://{url}"

    url = url.rstrip("/")
    # Если передан базовый путь API вида .../v1, дополняем до стандартного chat/completions
    if url.endswith("/v1"):
        url = f"{url}/chat/completions"

    return url


def get_ai_settings() -> dict[str, Any]:
    """Возвращает текущие настройки AI с учетом переменных окружения."""
    cfg = load_ai_config()

    endpoint = (
        os.environ.get("CAPRI_AI_ENDPOINT")
        or cfg.get("endpoint")
        or "https://api.openai.com/v1/chat/completions"
    )
    api_key = (
        os.environ.get("CAPRI_AI_API_KEY")
        or cfg.get("api_key")
        or ""
    )
    model = (
        os.environ.get("CAPRI_AI_MODEL")
        or cfg.get("model")
        or "gpt-4o-mini"
    )
    timeout = cfg.get("timeout", 60.0)
    try:
        if os.environ.get("CAPRI_AI_TIMEOUT"):
            timeout = float(os.environ["CAPRI_AI_TIMEOUT"])
    except (ValueError, TypeError):
        pass

    return {
        "endpoint": normalize_endpoint(endpoint),
        "api_key": str(api_key).strip(),
        "model": str(model).strip(),
        "temperature": float(cfg.get("temperature", 0.7)),
        "max_tokens": int(cfg.get("max_tokens", 256)),
        "timeout": float(timeout),
        "system_prompt": str(cfg.get("system_prompt", "")).strip(),
        "headers": dict(cfg.get("headers", {})),
    }


def _extract_error_detail(error: urllib.error.HTTPError) -> str:
    """Извлекает подробное описание ошибки из тела ответа HTTP."""
    try:
        raw_body = error.read().decode("utf-8", "replace")
        body = json.loads(raw_body)
    except Exception:
        return ""

    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            msg = err.get("message")
            if msg:
                return str(msg).strip()
        elif isinstance(err, str) and err.strip():
            return err.strip()
        msg = body.get("message") or body.get("detail")
        if msg:
            return str(msg).strip()
    return ""


def _extract_response_text(data: Any) -> str:
    """Извлекает текст ответа из различных форматов API (OpenAI, Anthropic и др.)."""
    if not isinstance(data, dict):
        return ""

    # 1. Формат OpenAI Chat Completions: choices[0].message.content
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if content:
                    return str(content).strip()
            text = first.get("text")
            if text:
                return str(text).strip()

    # 2. Формат Anthropic Messages: content[0].text
    content_list = data.get("content")
    if isinstance(content_list, list) and content_list:
        for item in content_list:
            if isinstance(item, dict) and item.get("type") == "text":
                val = item.get("text")
                if val:
                    return str(val).strip()
        first_item = content_list[0]
        if isinstance(first_item, dict) and "text" in first_item:
            return str(first_item["text"]).strip()

    # 3. Формат локальных моделей и сервисов: message.content или response
    msg = data.get("message")
    if isinstance(msg, dict) and msg.get("content"):
        return str(msg["content"]).strip()

    for key in ("response", "text", "answer", "output"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    return ""


def ask(
    prompt: str,
    *,
    history: list[dict[str, str]] | tuple[dict[str, str], ...] = (),
) -> str:
    """Отправляет запрос к настроенному кастомному AI API / эндпоинту и возвращает текст ответа."""
    settings = get_ai_settings()
    endpoint = settings["endpoint"]
    api_key = settings["api_key"]
    model_name = settings["model"]
    timeout = settings["timeout"]
    system_prompt = settings["system_prompt"]

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "temperature": settings["temperature"],
        "max_tokens": settings["max_tokens"],
        "stream": False,
    }

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": get_user_agent(),
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Добавляем кастомные заголовки из конфига (например, для OpenRouter или прокси)
    for k, v in settings["headers"].items():
        headers[k] = str(v)

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_data = json.load(response)
    except urllib.error.HTTPError as error:
        detail = _extract_error_detail(error)
        code = error.code
        if code in (401, 403):
            msg = detail or "проверь api_key в ai_config.json"
            raise AIError(f"Ошибка авторизации AI API ({code}): {msg}.") from error
        if code == 404:
            msg = detail or f"проверь URL {endpoint} и модель {model_name} в ai_config.json"
            raise AIError(f"AI эндпоинт или модель не найдены (404): {msg}.") from error
        if code == 429:
            msg = detail or "превышен лимит запросов, попробуй позже"
            raise AIError(f"Лимит запросов к AI API исчерпан (429): {msg}.") from error
        msg = detail or f"HTTP {code}"
        raise AIError(f"AI API ответил ошибкой: {msg}.") from error
    except TimeoutError as error:
        raise AIError(f"AI сервис не ответил за {timeout:.0f} сек.") from error
    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise AIError(f"AI сервис не ответил за {timeout:.0f} сек.") from error
        reason = str(error.reason)
        raise AIError(
            f"Не удалось подключиться к AI эндпоинту ({endpoint}): {reason}."
        ) from error
    except ValueError as error:
        raise AIError("AI сервис вернул некорректный ответ (не JSON).") from error

    answer = _extract_response_text(raw_data)
    if not answer:
        raise AIError("AI модель ответила пустым текстом.")
    return answer
