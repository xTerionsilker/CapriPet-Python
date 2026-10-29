from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Допустимые значения времени активности (мс): 5, 10 и 15 секунд.
ACTIVITY_TIMEOUT_OPTIONS_MS: tuple[int, ...] = (5_000, 10_000, 15_000)

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "screen": {
        "designated_screen": None,
    },
    "audio": {
        "designated_microphone": None,
        "volume": 50,
        "sfx_volume": 0.5,
        "media_volume": 0.6,
        "voice_enabled": True,
        "speech_sound_enabled": True,
        "effects_sound_enabled": True,
    },
    "appearance": {
        "skin": "default",
        "pose": "sit",
        "overlay_pose": "sit",
        "scale": 100,
    },
    "effects": {
        "glitches_enabled": True,
    },
    "window": {
        "position": None,
        "overlay_position": None,
        "terminal_position": None,
    },
    "behavior": {
        "inactivity_timeout_ms": 5000,
        "reminders_enabled": True,
    },
}

LEGACY_KEY_MAP = {
    "designated_screen": "screen.designated_screen",
    "designated_microphone": "audio.designated_microphone",
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Рекурсивно объединяет два словаря, создавая глубокую копию."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _resolve_config_dir() -> Path:
    """Возвращает базовую директорию для хранения конфигурации с безопасным fallback."""
    # 1. Системный каталог ~/.config/capri
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base_config = Path(xdg) if xdg else Path.home() / ".config"
    home_dir = base_config / "capri"
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
        test_file = home_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return home_dir
    except OSError:
        pass

    # 2. Локальный каталог проекта .capri
    local_dir = Path(__file__).resolve().parent.parent.parent / ".capri"
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        return local_dir
    except OSError:
        pass

    # 3. Временная директория
    return Path("/tmp")


def _get_default_config_path() -> Path:
    config_dir = _resolve_config_dir()
    if config_dir == Path("/tmp"):
        return Path("/tmp/capri_config.json")
    return config_dir / "config.json"


class ConfigManager:
    """Менеджер конфигурации CapriPet с поддержкой валидации, миграции и атомарной записи."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._is_custom_path = config_path is not None
        self._config_path = config_path or _get_default_config_path()
        self._cached_config: dict[str, Any] | None = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    def _migrate_legacy_settings(self) -> dict[str, Any] | None:
        """Проверяет наличие старого settings.json и мигрирует данные в новую структуру."""
        legacy_candidates = [self._config_path.parent / "settings.json"]
        if not self._is_custom_path:
            legacy_candidates.extend([
                Path.home() / ".config" / "capri" / "settings.json",
                Path(__file__).resolve().parent.parent.parent / ".capri" / "settings.json",
                Path("/tmp/capri_settings.json"),
            ])

        for legacy_path in legacy_candidates:
            if legacy_path.is_file():
                try:
                    with open(legacy_path, "r", encoding="utf-8") as f:
                        old_data = json.load(f)
                    if not isinstance(old_data, dict):
                        continue

                    migrated = copy.deepcopy(DEFAULT_CONFIG)
                    if "designated_screen" in old_data:
                        migrated["screen"]["designated_screen"] = old_data["designated_screen"] or None
                    if "designated_microphone" in old_data:
                        migrated["audio"]["designated_microphone"] = old_data["designated_microphone"] or None

                    logger.info("Миграция конфигурации из %s выполнена успешно.", legacy_path)
                    return migrated
                except Exception as e:
                    logger.warning("Ошибка чтения устаревшего файла настроек %s: %s", legacy_path, e)
        return None

    def _validate_and_sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Проверяет типы и границы критичных полей, восстанавливая дефолты при необходимости."""
        config = _deep_merge(DEFAULT_CONFIG, data)

        # Проверка позы
        if config["appearance"].get("overlay_pose") not in ("sit", "stay", "crouch"):
            config["appearance"]["overlay_pose"] = "sit"
        if config["appearance"].get("pose") not in ("sit", "stay", "crouch"):
            config["appearance"]["pose"] = config["appearance"]["overlay_pose"]

        # Общая громкость программы (в процентах)
        try:
            volume = int(config["audio"].get("volume", DEFAULT_CONFIG["audio"]["volume"]))
            if volume not in (25, 50, 75, 100):
                volume = DEFAULT_CONFIG["audio"]["volume"]
            config["audio"]["volume"] = volume
        except (ValueError, TypeError):
            config["audio"]["volume"] = DEFAULT_CONFIG["audio"]["volume"]

        # Громкость
        for vol_key in ("sfx_volume", "media_volume"):
            try:
                val = float(config["audio"].get(vol_key, DEFAULT_CONFIG["audio"][vol_key]))
                config["audio"][vol_key] = max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                config["audio"][vol_key] = DEFAULT_CONFIG["audio"][vol_key]

        # Булевы флаги
        config["audio"]["voice_enabled"] = bool(config["audio"].get("voice_enabled", True))
        config["audio"]["speech_sound_enabled"] = bool(config["audio"].get("speech_sound_enabled", True))
        config["audio"]["effects_sound_enabled"] = bool(config["audio"].get("effects_sound_enabled", True))
        config["effects"]["glitches_enabled"] = bool(config["effects"].get("glitches_enabled", True))

        # Масштаб спрайта питомца
        try:
            scale = int(config["appearance"].get("scale", 100))
            if scale not in (50, 75, 100, 125, 150):
                scale = 100
            config["appearance"]["scale"] = scale
        except (ValueError, TypeError):
            config["appearance"]["scale"] = 100

        # Время активности до скрытия питомца
        try:
            inactivity = int(config["behavior"].get("inactivity_timeout_ms", 5000))
        except (ValueError, TypeError):
            inactivity = ACTIVITY_TIMEOUT_OPTIONS_MS[0]
        if inactivity not in ACTIVITY_TIMEOUT_OPTIONS_MS:
            inactivity = ACTIVITY_TIMEOUT_OPTIONS_MS[0]
        config["behavior"]["inactivity_timeout_ms"] = inactivity
        config["behavior"]["reminders_enabled"] = bool(
            config["behavior"].get("reminders_enabled", True)
        )

        # Координаты
        for pos_key in ("position", "overlay_position", "terminal_position"):
            pos = config["window"].get(pos_key)
            if pos is not None:
                if not (isinstance(pos, dict) and "x" in pos and "y" in pos and isinstance(pos["x"], (int, float)) and isinstance(pos["y"], (int, float))):
                    config["window"][pos_key] = None
                else:
                    config["window"][pos_key] = {"x": int(pos["x"]), "y": int(pos["y"])}

        return config

    def load_config(self, force_reload: bool = False) -> dict[str, Any]:
        """Загружает конфигурацию из файла с фолбэком на дефолты и миграцию."""
        if self._cached_config is not None and not force_reload:
            return copy.deepcopy(self._cached_config)

        if not self._config_path.is_file():
            # Попытка миграции старого settings.json
            migrated = self._migrate_legacy_settings()
            if migrated is not None:
                config = self._validate_and_sanitize(migrated)
                self.save_config(config)
                self._cached_config = config
                return copy.deepcopy(config)

            config = copy.deepcopy(DEFAULT_CONFIG)
            self._cached_config = config
            return copy.deepcopy(config)

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            if not isinstance(raw_data, dict):
                logger.warning("Файл конфигурации %s поврежден (не словарь). Используются дефолты.", self._config_path)
                config = copy.deepcopy(DEFAULT_CONFIG)
            else:
                config = self._validate_and_sanitize(raw_data)
        except Exception as e:
            logger.warning("Ошибка чтения конфигурации из %s: %s. Используются дефолты.", self._config_path, e)
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
            logger.warning("Не удалось сохранить конфигурацию в %s: %s", target, e)

    def get_value(self, path: str, default: Any = None) -> Any:
        """Получает значение по пути dot-notation, например 'audio.sfx_volume'."""
        if path in LEGACY_KEY_MAP:
            path = LEGACY_KEY_MAP[path]

        config = self.load_config()
        keys = path.split(".")
        current: Any = config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current if current is not None else default

    def set_value(self, path: str, value: Any, auto_save: bool = True) -> None:
        """Устанавливает значение по dot-notation пути и опционально сохраняет файл."""
        if path in LEGACY_KEY_MAP:
            path = LEGACY_KEY_MAP[path]

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


# Глобальный экземпляр менеджера
_global_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    return _global_manager


def load_config() -> dict[str, Any]:
    return _global_manager.load_config()


def save_config(config: dict[str, Any]) -> None:
    _global_manager.save_config(config)


def get_config_value(path: str, default: Any = None) -> Any:
    return _global_manager.get_value(path, default)


def set_config_value(path: str, value: Any) -> None:
    _global_manager.set_value(path, value)


# Совместимость с предыдущим API settings.py
def load_settings() -> dict[str, Any]:
    return load_config()


def save_settings(settings: dict[str, Any]) -> None:
    save_config(settings)


def get_setting(key: str, default: Any = None) -> Any:
    return get_config_value(key, default)


def set_setting(key: str, value: Any) -> None:
    set_config_value(key, value)
