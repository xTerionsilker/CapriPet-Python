"""Управление конфигурацией CapriPet: чтение, валидация и сохранение."""

from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Literal

from fake_useragent import UserAgent
from platformdirs import user_config_dir
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

_resolved_user_agent: str | None = None
_ua_lock = threading.Lock()
_DEFAULT_FALLBACK_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

ACTIVITY_TIMEOUT_OPTIONS_MS: tuple[int, ...] = (5_000, 10_000, 15_000)
GLITCH_INTENSITY_OPTIONS: tuple[str, ...] = ("weak", "medium", "strong")


class WindowPosition(BaseModel):
    """Координаты положения окна на рабочем столе."""

    x: int
    y: int


class ScreenConfig(BaseModel):
    """Конфигурация целевого монитора для отображения питомца."""

    designated_screen: str | None = None


class AudioConfig(BaseModel):
    """Параметры аудиосистемы, громкости и распознавания речи."""

    designated_microphone: str | None = None
    volume: int = 50
    sfx_volume: float = Field(default=0.5, ge=0.0, le=1.0)
    media_volume: float = Field(default=0.6, ge=0.0, le=1.0)
    voice_enabled: bool = True
    speech_sound_enabled: bool = True
    effects_sound_enabled: bool = True
    asr_backend: Literal["vosk", "whisper"] = "vosk"

    @field_validator("volume", mode="before")
    @classmethod
    def validate_volume(cls, v: Any) -> int:
        try:
            val = int(v)
            return val if val in (25, 50, 75, 100) else 50
        except Exception:
            return 50

    @field_validator("sfx_volume", "media_volume", mode="before")
    @classmethod
    def clamp_vol(cls, v: Any) -> float:
        try:
            return max(0.0, min(1.0, float(v)))
        except Exception:
            return 0.5


class AppearanceConfig(BaseModel):
    """Настройки внешнего вида, скина, позы и масштаба питомца."""

    skin: str = "default"
    pose: Literal["sit", "stay", "crouch"] = "sit"
    overlay_pose: Literal["sit", "stay", "crouch"] = "sit"
    scale: int = 100

    @field_validator("scale", mode="before")
    @classmethod
    def validate_scale(cls, v: Any) -> int:
        try:
            val = int(v)
            return val if val in (50, 75, 100, 125, 150) else 100
        except Exception:
            return 100

    @field_validator("pose", "overlay_pose", mode="before")
    @classmethod
    def validate_pose(cls, v: Any) -> str:
        return v if v in ("sit", "stay", "crouch") else "sit"

    @model_validator(mode="before")
    @classmethod
    def sync_pose_fallback(cls, data: Any) -> Any:
        if (
            isinstance(data, dict)
            and "overlay_pose" in data
            and "pose" not in data
        ):
            data["pose"] = data["overlay_pose"]
        return data


class EffectsConfig(BaseModel):
    """Настройки экранных глитч-эффектов и их интенсивности."""

    glitches_enabled: bool = True
    glitch_intensity: Literal["weak", "medium", "strong"] = "weak"

    @field_validator("glitch_intensity", mode="before")
    @classmethod
    def validate_intensity(cls, v: Any) -> str:
        s = str(v).lower()
        return s if s in GLITCH_INTENSITY_OPTIONS else "weak"


class WindowConfig(BaseModel):
    """Конфигурация сохранённых позиций окон и оверлеев."""

    position: WindowPosition | None = None
    overlay_position: WindowPosition | None = None
    terminal_position: WindowPosition | None = None

    @field_validator(
        "position", "overlay_position", "terminal_position", mode="before"
    )
    @classmethod
    def validate_pos(cls, v: Any) -> dict[str, int] | None:
        if isinstance(v, dict) and "x" in v and "y" in v:
            try:
                return {"x": int(v["x"]), "y": int(v["y"])}
            except Exception:
                return None
        return None


class BehaviorConfig(BaseModel):
    """Параметры поведения питомца, таймаута неактивности и напоминаний."""

    inactivity_timeout_ms: int = 5000
    reminders_enabled: bool = True
    reminder_min_interval_ms: int = 600_000
    reminder_max_interval_ms: int = 3_600_000

    @field_validator("inactivity_timeout_ms", mode="before")
    @classmethod
    def validate_timeout(cls, v: Any) -> int:
        try:
            val = int(v)
            return val if val in ACTIVITY_TIMEOUT_OPTIONS_MS else 5_000
        except Exception:
            return 5_000

    @model_validator(mode="after")
    def validate_intervals(self) -> BehaviorConfig:
        min_remind = max(5_000, int(self.reminder_min_interval_ms))
        max_remind = max(min_remind, int(self.reminder_max_interval_ms))
        self.reminder_min_interval_ms = min_remind
        self.reminder_max_interval_ms = max_remind
        return self


class NetworkConfig(BaseModel):
    """Сетевая конфигурация и параметры User-Agent."""

    user_agent: str | None = None


class DiscordConfig(BaseModel):
    """Настройки интеграции с Discord Rich Presence."""

    enabled: bool = True
    client_id: str = "1567968896277938266"


class GameModeConfig(BaseModel):
    """Параметры детекции игр и подавления уведомлений."""

    suppression_enabled: bool = True
    cooldown_seconds: float = 3.0
    whitelist: list[str] = Field(default_factory=list)
    blacklist: list[str] = Field(
        default_factory=lambda: [
            "steam.exe",
            "steamwebhelper.exe",
            "epicgameslauncher.exe",
            "unrealcefsubprocess.exe",
            "unitycrashhandler64.exe",
            "riotclientux.exe",
            "galaxyclient.exe",
            "battlenet.exe",
        ]
    )


class CapriConfig(BaseModel):
    """Корневая модель конфигурации приложения CapriPet."""

    version: int = 1
    screen: ScreenConfig = Field(default_factory=ScreenConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    appearance: AppearanceConfig = Field(default_factory=AppearanceConfig)
    effects: EffectsConfig = Field(default_factory=EffectsConfig)
    window: WindowConfig = Field(default_factory=WindowConfig)
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig)
    game_mode: GameModeConfig = Field(default_factory=GameModeConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)


DEFAULT_CONFIG: dict[str, Any] = CapriConfig().model_dump()

# Псевдонимы конфигурации для совместимости
InactivityConfig = BehaviorConfig
OverlayConfig = AppearanceConfig
VoskConfig = AudioConfig
AppConfig = CapriConfig


def _get_project_root() -> Path:
    """Возвращает корень проекта CapriPet."""
    return Path(__file__).resolve().parent.parent.parent


def _resolve_config_dir() -> Path:
    """Возвращает базовую директорию для хранения конфигурации с безопасным fallback."""
    env_dir = os.environ.get("CAPRI_CONFIG_DIR")
    if env_dir:
        path = Path(env_dir).expanduser().resolve()
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception as e:
            logger.warning(
                "Не удалось использовать CAPRI_CONFIG_DIR=%s: %s",
                env_dir,
                e,
            )

    local_dir = _get_project_root() / ".capri"
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        test_file = local_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return local_dir
    except OSError:
        pass

    home_dir = Path(user_config_dir("capri"))
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
        test_file = home_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return home_dir
    except OSError:
        pass

    return Path(tempfile.gettempdir())


def _get_default_config_path() -> Path:
    """Определяет путь к файлу конфигурации."""
    config_dir = _resolve_config_dir()
    temp_dir = Path(tempfile.gettempdir())
    if config_dir == temp_dir:
        return temp_dir / "capri_config.json"
    return config_dir / "config.json"


class ConfigManager:
    """Менеджер конфигурации с Pydantic валидацией, кэшированием и атомарным сохранением."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._is_custom_path = config_path is not None
        self._config_path = config_path or _get_default_config_path()
        self._cached_config: dict[str, Any] | None = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    def _validate_and_sanitize(
        self, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Валидирует данные через Pydantic-модель CapriConfig."""
        try:
            model = CapriConfig.model_validate(
                data if isinstance(data, dict) else {}
            )
            return model.model_dump()
        except Exception as e:
            logger.warning(
                "Ошибка валидации настроек Pydantic: %s. Применяются дефолты.",
                e,
            )
            return copy.deepcopy(DEFAULT_CONFIG)

    def load_config(self, force_reload: bool = False) -> dict[str, Any]:
        """Загружает конфигурацию из файла с Pydantic валидацией."""
        if self._cached_config is not None and not force_reload:
            return copy.deepcopy(self._cached_config)

        if not self._config_path.is_file():
            config = copy.deepcopy(DEFAULT_CONFIG)
            self._cached_config = config
            return copy.deepcopy(config)

        try:
            with open(self._config_path, encoding="utf-8") as f:
                raw_data = json.load(f)
            if not isinstance(raw_data, dict):
                logger.warning(
                    "Файл конфигурации %s поврежден (не словарь). Используются дефолты.",
                    self._config_path,
                )
                config = copy.deepcopy(DEFAULT_CONFIG)
            else:
                config = self._validate_and_sanitize(raw_data)
        except Exception as e:
            logger.warning(
                "Ошибка чтения конфигурации из %s: %s. Используются дефолты.",
                self._config_path,
                e,
            )
            config = copy.deepcopy(DEFAULT_CONFIG)

        self._cached_config = config
        return copy.deepcopy(config)

    def save_config(self, config: dict[str, Any]) -> None:
        """Атомарно сохраняет конфигурацию во временный файл и заменяет целевой."""
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
            logger.warning(
                "Не удалось сохранить конфигурацию в %s: %s", target, e
            )

    def get_value(self, path: str, default: Any = None) -> Any:
        """Получает значение по пути dot-notation, например 'audio.sfx_volume'."""
        config = self.load_config()
        keys = path.split(".")
        current: Any = config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current if current is not None else default

    def set_value(
        self, path: str, value: Any, auto_save: bool = True
    ) -> None:
        """Устанавливает значение по dot-notation пути и опционально сохраняет файл."""
        config = self.load_config()
        keys = path.split(".")
        current = config
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

        sanitized = self._validate_and_sanitize(config)
        if auto_save:
            self.save_config(sanitized)
        else:
            self._cached_config = copy.deepcopy(sanitized)


_global_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    return _global_manager


def load_config() -> dict[str, Any]:
    return _global_manager.load_config()


def save_config(config: dict[str, Any]) -> None:
    _global_manager.save_config(config)


def get_config_value(path: str, default: Any = None) -> Any:
    return _global_manager.get_value(path, default=default)


def set_config_value(
    path: str, value: Any, auto_save: bool = True
) -> None:
    _global_manager.set_value(path, value, auto_save=auto_save)


def init_user_agent_async() -> None:
    thread = threading.Thread(
        target=get_user_agent,
        name="capri-user-agent-init",
        daemon=True,
    )
    thread.start()


def get_user_agent() -> str:
    global _resolved_user_agent

    if _resolved_user_agent is not None:
        return _resolved_user_agent

    with _ua_lock:
        if _resolved_user_agent is not None:
            return _resolved_user_agent

        try:
            custom_ua = get_config_value("network.user_agent")
            if (
                custom_ua
                and isinstance(custom_ua, str)
                and custom_ua.strip()
            ):
                _resolved_user_agent = custom_ua.strip()
                logger.debug(
                    "Используется пользовательский User-Agent из конфига: %s",
                    _resolved_user_agent,
                )
                return _resolved_user_agent
        except Exception as e:
            logger.debug(
                "Не удалось прочитать User-Agent из конфига: %s", e
            )

        try:
            ua = UserAgent(platforms="pc", fallback=_DEFAULT_FALLBACK_UA)
            _resolved_user_agent = str(ua.random)
            logger.debug(
                "Сгенерирован User-Agent через fake-useragent: %s",
                _resolved_user_agent,
            )
        except Exception as e:
            logger.warning(
                "Ошибка fake-useragent, используется fallback: %s", e
            )
            _resolved_user_agent = _DEFAULT_FALLBACK_UA

        return _resolved_user_agent
