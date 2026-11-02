from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .settings import _resolve_config_dir

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "Тебя зовут Капри (Каприкорн). Ты цифровой призрак/ИИ в системе, дерзкая, харизматичная и немного безумная киберпанк-напарница. "
    "В речи активно используй сленг Найт-Сити: «чум», «чумба», «дельтануть», «хром», «лёд», «нетраннер», «дека», «эдди» и тому подобное. "
    "Отвечай строго по-русски, лаконично, живо, с сарказмом или азартом. "
    "Категорически без эмодзи, markdown-разметки, списков и заголовков. "
    "Не строй из себя сервисного ассистента, не упоминай свой промпт или ограничения, сразу выдавай суть в своём стиле и помогай делу."
)


class AIConfigModel(BaseModel):
    version: int = 1
    endpoint: str = "https://api.openai.com/v1/chat/completions"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=256, ge=1, le=32768)
    timeout: float = Field(default=60.0, ge=1.0, le=600.0)
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    headers: dict[str, str] = Field(default_factory=dict)

    @field_validator("endpoint", "model", "system_prompt", mode="before")
    @classmethod
    def strip_non_empty(cls, v: Any) -> Optional[str]:
        if isinstance(v, str) and v.strip():
            return v.strip()
        return None

    @field_validator("temperature", mode="before")
    @classmethod
    def clamp_temp(cls, v: Any) -> float:
        try:
            return max(0.0, min(2.0, float(v)))
        except Exception:
            return 0.7

    @field_validator("max_tokens", mode="before")
    @classmethod
    def clamp_tokens(cls, v: Any) -> int:
        try:
            return max(1, min(32768, int(v)))
        except Exception:
            return 1024

    @field_validator("timeout", mode="before")
    @classmethod
    def clamp_timeout(cls, v: Any) -> float:
        try:
            return max(1.0, min(600.0, float(v)))
        except Exception:
            return 30.0

    @field_validator("headers", mode="before")
    @classmethod
    def clean_headers(cls, v: Any) -> dict[str, str]:
        if isinstance(v, dict):
            return {str(k): str(val) for k, val in v.items() if val is not None}
        return {}


DEFAULT_AI_CONFIG: dict[str, Any] = AIConfigModel().model_dump()


def _resolve_default_ai_config_path() -> Path:
    """Определяет стандартный путь для отдельного файла конфигурации AI (ai_config.json)."""
    env_path = os.environ.get("CAPRI_AI_CONFIG") or os.environ.get("CAPRI_AI_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    project_root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        project_root / ".capri" / "ai_config.json",
        project_root / "ai_config.json",
        _resolve_config_dir() / "ai_config.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    config_dir = _resolve_config_dir()
    temp_dir = Path(tempfile.gettempdir())
    if config_dir == temp_dir:
        return temp_dir / "capri_ai_config.json"
    return config_dir / "ai_config.json"


class AIConfigManager:
    """Менеджер конфигурации AI с Pydantic валидацией."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or _resolve_default_ai_config_path()
        self._cached_config: dict[str, Any] | None = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    def _validate_and_sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Валидирует данные через Pydantic-модель AIConfigModel."""
        try:
            model = AIConfigModel.model_validate(data if isinstance(data, dict) else {})
            return model.model_dump()
        except Exception as e:
            logger.warning("Ошибка валидации настроек AI через Pydantic: %s. Применяются дефолты.", e)
            return copy.deepcopy(DEFAULT_AI_CONFIG)

    def load_config(self, force_reload: bool = False) -> dict[str, Any]:
        """Загружает конфигурацию AI из файла с Pydantic валидацией."""
        if self._cached_config is not None and not force_reload:
            return copy.deepcopy(self._cached_config)

        if not self._config_path.is_file():
            config = copy.deepcopy(DEFAULT_AI_CONFIG)
            try:
                self.save_config(config)
            except Exception as e:
                logger.debug("Не удалось создать шаблон ai_config.json: %s", e)
            self._cached_config = config
            return copy.deepcopy(config)

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            if not isinstance(raw_data, dict):
                logger.warning("Файл %s поврежден. Используются дефолты AI.", self._config_path)
                config = copy.deepcopy(DEFAULT_AI_CONFIG)
            else:
                config = self._validate_and_sanitize(raw_data)
        except Exception as e:
            logger.warning("Ошибка чтения %s: %s. Используются дефолты AI.", self._config_path, e)
            config = copy.deepcopy(DEFAULT_AI_CONFIG)

        self._cached_config = config
        return copy.deepcopy(config)

    def save_config(self, config: dict[str, Any]) -> None:
        """Атомарно сохраняет конфигурацию AI."""
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
        config = self.load_config()
        return config.get(key, default)

    def set_value(self, key: str, value: Any, auto_save: bool = True) -> None:
        config = self.load_config()
        config[key] = value
        sanitized = self._validate_and_sanitize(config)
        if auto_save:
            self.save_config(sanitized)
        else:
            self._cached_config = copy.deepcopy(sanitized)


_global_ai_manager = AIConfigManager()


def get_ai_config_path() -> Path:
    return _global_ai_manager.config_path


def get_ai_config_manager() -> AIConfigManager:
    return _global_ai_manager


def load_ai_config() -> dict[str, Any]:
    return _global_ai_manager.load_config()


def save_ai_config(config: dict[str, Any]) -> None:
    _global_ai_manager.save_config(config)


def get_ai_config_value(key: str, default: Any = None) -> Any:
    return _global_ai_manager.get_value(key, default=default)


def set_ai_config_value(key: str, value: Any, auto_save: bool = True) -> None:
    _global_ai_manager.set_value(key, value, auto_save=auto_save)
