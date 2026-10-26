from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _get_settings_file() -> Path:
    """Возвращает путь к файлу настроек с фолбэком, если ~/.config защищен от записи."""
    # 1. Предпочтительный системный путь ~/.config/capri/settings.json
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base_config = Path(xdg) if xdg else Path.home() / ".config"
    home_dir = base_config / "capri"
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
        test_file = home_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return home_dir / "settings.json"
    except OSError:
        pass

    # 2. Фолбэк на каталог проекта .capri/settings.json
    local_dir = Path(__file__).resolve().parent.parent.parent / ".capri"
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        return local_dir / "settings.json"
    except OSError:
        pass

    # 3. Фолбэк на временную директорию
    return Path("/tmp/capri_settings.json")


def load_settings() -> dict[str, Any]:
    """Загружает пользовательские настройки Capri."""
    target = _get_settings_file()
    if not target.is_file():
        return {}
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(settings: dict[str, Any]) -> None:
    """Сохраняет настройки Capri."""
    target = _get_settings_file()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_setting(key: str, default: Any = None) -> Any:
    return load_settings().get(key, default)


def set_setting(key: str, value: Any) -> None:
    data = load_settings()
    data[key] = value
    save_settings(data)
