from __future__ import annotations

import copy
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from .settings import _resolve_config_dir

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "Тебя зовут Капри (Каприкорн). Ты цифровой призрак/ИИ в системе, дерзкая, харизматичная и немного безумная киберпанк-напарница. "
    "В речи активно используй сленг Найт-Сити: «чум», «чумба», «дельтануть», «хром», «лёд», «нетраннер», «дека», «эдди» и тому подобное. "
    "Отвечай строго по-русски, лаконично, живо, с сарказмом или азартом. "
    "Категорически без эмодзи, markdown-разметки, списков и заголовков. "
    "Не строй из себя сервисного ассистента, не упоминай свой промпт или ограничения, сразу выдавай суть в своём стиле и помогай делу."
)

DEFAULT_AI_CONFIG: dict[str, Any] = {
    "version": 1,
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "api_key": "",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 256,
    "timeout": 60.0,
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "headers": {},
}


def _resolve_default_ai_config_path() -> Path:
    """Определяет стандартный путь для отдельного файла конфигурации AI (ai_config.json)."""
    env_path = os.environ.get("CAPRI_AI_CONFIG")
    if env_path:
        return Path(env_path).expanduser().resolve()

    # Проверка существующих файлов в известных местах
    project_root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        project_root / ".capri" / "ai_config.json",
        project_root / "ai_config.json",
        _resolve_config_dir() / "ai_config.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    # Если файл ещё не создан:
    # 1. Если есть локальный каталог .capri в проекте, предпочитаем его
    local_capri = project_root / ".capri"
    if local_capri.is_dir():
        return local_capri / "ai_config.json"

    # 2. Иначе каталог конфигурации системы/пользователя
    config_dir = _resolve_config_dir()
    temp_dir = Path(tempfile.gettempdir())
    if config_dir == temp_dir:
        return temp_dir / "capri_ai_config.json"
    return config_dir / "ai_config.json"


class AIConfigManager:
    """Менеджер отдельной конфигурации AI с поддержкой кастомных API, эндпоинтов и ключей."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._is_custom_path = config_path is not None
        self._config_path = config_path or _resolve_default_ai_config_path()
        self._cached_config: dict[str, Any] | None = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    def _validate_and_sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Проверяет типы полей конфигурации и подставляет дефолтные значения при необходимости."""
        config = copy.deepcopy(DEFAULT_AI_CONFIG)
        if not isinstance(data, dict):
            return config

        # Endpoint
        endpoint = data.get("endpoint")
        if isinstance(endpoint, str) and endpoint.strip():
            config["endpoint"] = endpoint.strip()

        # API Key
        api_key = data.get("api_key")
        if isinstance(api_key, str):
            config["api_key"] = api_key.strip()

        # Model
        model = data.get("model")
        if isinstance(model, str) and model.strip():
            config["model"] = model.strip()

        # Temperature
        try:
            temp = float(data.get("temperature", DEFAULT_AI_CONFIG["temperature"]))
            config["temperature"] = max(0.0, min(2.0, temp))
        except (ValueError, TypeError):
            config["temperature"] = DEFAULT_AI_CONFIG["temperature"]

        # Max tokens
        try:
            tokens = int(data.get("max_tokens", DEFAULT_AI_CONFIG["max_tokens"]))
            config["max_tokens"] = max(1, min(32768, tokens))
        except (ValueError, TypeError):
            config["max_tokens"] = DEFAULT_AI_CONFIG["max_tokens"]

        # Timeout
        try:
            timeout = float(data.get("timeout", DEFAULT_AI_CONFIG["timeout"]))
            config["timeout"] = max(1.0, min(600.0, timeout))
        except (ValueError, TypeError):
            config["timeout"] = DEFAULT_AI_CONFIG["timeout"]

        # System prompt
        system_prompt = data.get("system_prompt")
        if isinstance(system_prompt, str) and system_prompt.strip():
            config["system_prompt"] = system_prompt.strip()

        # Custom headers
        headers = data.get("headers")
        if isinstance(headers, dict):
            config["headers"] = {
                str(k): str(v) for k, v in headers.items() if v is not None
            }

        return config

    def load_config(self, force_reload: bool = False) -> dict[str, Any]:
        """Загружает отдельную конфигурацию AI из файла с фолбэком на дефолты."""
        if self._cached_config is not None and not force_reload:
            return copy.deepcopy(self._cached_config)

        if not self._config_path.is_file():
            config = copy.deepcopy(DEFAULT_AI_CONFIG)
            # Автоматически создаем начальный шаблон конфига для удобства пользователя
            try:
                self.save_config(config)
            except Exception as e:
                logger.debug("Не удалось создать начальный ai_config.json: %s", e)
            self._cached_config = config
            return copy.deepcopy(config)

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            if not isinstance(raw_data, dict):
                logger.warning(
                    "Файл конфигурации AI %s поврежден (не словарь). Используются дефолты.",
                    self._config_path,
                )
                config = copy.deepcopy(DEFAULT_AI_CONFIG)
            else:
                config = self._validate_and_sanitize(raw_data)
        except Exception as e:
            logger.warning(
                "Ошибка чтения конфигурации AI из %s: %s. Используются дефолты.",
                self._config_path,
                e,
            )
            config = copy.deepcopy(DEFAULT_AI_CONFIG)

        self._cached_config = config
        return copy.deepcopy(config)

    def save_config(self, config: dict[str, Any]) -> None:
        """Атомарно сохраняет конфигурацию AI во временный файл и заменяет целевой."""
        target = self._config_path
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp_target = target.with_suffix(f"{target.suffix}.tmp")
            with open(tmp_target, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_target, target)
            self._cached_config = copy.deepcopy(config)
        except Exception as e:
            logger.warning("Не удалось сохранить конфигурацию AI в %s: %s", target, e)

    def get_value(self, key: str, default: Any = None) -> Any:
        """Получает значение параметра конфигурации AI."""
        config = self.load_config()
        if key in config:
            return config[key]
        keys = key.split(".")
        current: Any = config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current if current is not None else default

    def set_value(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Устанавливает значение параметра конфигурации AI."""
        config = self.load_config()
        if "." in key:
            keys = key.split(".")
            current = config
            for k in keys[:-1]:
                if k not in current or not isinstance(current[k], dict):
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value
        else:
            config[key] = value

        sanitized = self._validate_and_sanitize(config)
        if auto_save:
            self.save_config(sanitized)
        else:
            self._cached_config = copy.deepcopy(sanitized)


_global_ai_manager = AIConfigManager()


def get_ai_config_manager() -> AIConfigManager:
    return _global_ai_manager


def load_ai_config() -> dict[str, Any]:
    return _global_ai_manager.load_config()


def save_ai_config(config: dict[str, Any]) -> None:
    _global_ai_manager.save_config(config)


def get_ai_config_value(key: str, default: Any = None) -> Any:
    return _global_ai_manager.get_value(key, default)


def set_ai_config_value(key: str, value: Any) -> None:
    _global_ai_manager.set_value(key, value)


def get_ai_config_path() -> Path:
    return _global_ai_manager.config_path
