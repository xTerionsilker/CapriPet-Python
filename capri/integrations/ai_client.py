from __future__ import annotations

import logging
import os
from typing import Any, Sequence

import openai
from openai import OpenAI

from ..core.ai_config import load_ai_config
from ..core.settings import get_user_agent

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
_CHAT_SUFFIX = "/chat/completions"


class AIError(RuntimeError):
    pass


def normalize_endpoint(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        return DEFAULT_ENDPOINT

    if "://" not in url:
        if url.startswith(("localhost", "127.0.0.1")):
            url = f"http://{url}"
        else:
            url = f"https://{url}"

    url = url.rstrip("/")
    if url.endswith("/v1"):
        url = f"{url}{_CHAT_SUFFIX}"
    return url


def _base_url(endpoint: str) -> str:
    if endpoint.endswith(_CHAT_SUFFIX):
        return endpoint[: -len(_CHAT_SUFFIX)]
    return endpoint


def get_ai_settings() -> dict[str, Any]:
    config = load_ai_config()

    endpoint = (
        os.environ.get("CAPRI_AI_ENDPOINT")
        or config.get("endpoint")
        or DEFAULT_ENDPOINT
    )
    api_key = os.environ.get("CAPRI_AI_API_KEY") or config.get("api_key") or ""
    model = os.environ.get("CAPRI_AI_MODEL") or config.get("model") or "gpt-4o-mini"

    timeout = config.get("timeout", 60.0)
    try:
        if os.environ.get("CAPRI_AI_TIMEOUT"):
            timeout = float(os.environ["CAPRI_AI_TIMEOUT"])
    except (ValueError, TypeError):
        pass

    return {
        "endpoint": normalize_endpoint(str(endpoint)),
        "api_key": str(api_key).strip(),
        "model": str(model).strip(),
        "temperature": float(config.get("temperature", 0.7)),
        "max_tokens": int(config.get("max_tokens", 256)),
        "timeout": float(timeout),
        "system_prompt": str(config.get("system_prompt", "")).strip(),
        "headers": dict(config.get("headers", {})),
    }


def _error_detail(error: openai.APIStatusError) -> str:
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        inner = body.get("error")
        if isinstance(inner, dict) and inner.get("message"):
            return str(inner["message"]).strip()
        if isinstance(inner, str) and inner.strip():
            return inner.strip()
        for key in ("message", "detail"):
            if body.get(key):
                return str(body[key]).strip()
    return ""


def _client(settings: dict[str, Any]) -> OpenAI:
    headers = {"User-Agent": get_user_agent(), **settings["headers"]}
    return OpenAI(
        api_key=settings["api_key"] or "capri-local",
        base_url=_base_url(settings["endpoint"]),
        timeout=settings["timeout"],
        max_retries=0,
        default_headers=headers,
    )


def _build_messages(
    prompt: str,
    history: Sequence[dict[str, str]],
    system_prompt: str,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    return messages


def ask(
    prompt: str,
    *,
    history: Sequence[dict[str, str]] = (),
) -> str:
    settings = get_ai_settings()
    endpoint = settings["endpoint"]
    timeout = settings["timeout"]
    model_name = settings["model"]
    client = _client(settings)

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=_build_messages(prompt, history, settings["system_prompt"]),
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            stream=False,
        )
    except openai.AuthenticationError as error:
        detail = _error_detail(error) or "проверь api_key в ai_config.json"
        raise AIError(f"Ошибка авторизации AI API ({error.status_code}): {detail}.") from error
    except openai.NotFoundError as error:
        detail = _error_detail(error) or f"проверь URL {endpoint} и модель {model_name} в ai_config.json"
        raise AIError(f"AI эндпоинт или модель не найдены (404): {detail}.") from error
    except openai.RateLimitError as error:
        detail = _error_detail(error) or "превышен лимит запросов, попробуй позже"
        raise AIError(f"Лимит запросов к AI API исчерпан (429): {detail}.") from error
    except openai.APITimeoutError as error:
        raise AIError(f"AI сервис не ответил за {timeout:.0f} сек.") from error
    except openai.APIConnectionError as error:
        raise AIError(
            f"Не удалось подключиться к AI эндпоинту ({endpoint}): {error}."
        ) from error
    except openai.APIStatusError as error:
        detail = _error_detail(error) or f"HTTP {error.status_code}"
        raise AIError(f"AI API ответил ошибкой: {detail}.") from error
    except openai.OpenAIError as error:
        raise AIError(f"AI сервис вернул некорректный ответ: {error}.") from error

    if not completion.choices:
        raise AIError("AI модель ответила пустым текстом.")

    answer = (completion.choices[0].message.content or "").strip()
    if not answer:
        raise AIError("AI модель ответила пустым текстом.")
    return answer
