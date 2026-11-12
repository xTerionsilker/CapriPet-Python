"""Тесты расположения и изоляции конфигурационных файлов CapriPet."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from capri.core.settings import (
    ConfigManager,
    _get_default_config_path,
    get_config_dir,
)
from capri.integrations import spotify


class TestConfigStorage(unittest.TestCase):
    """Проверка чистого хранения конфигурации в пользовательском каталоге."""

    def test_get_config_dir_env_override(self) -> None:
        """Переменная окружения CAPRI_CONFIG_DIR имеет высший приоритет."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"CAPRI_CONFIG_DIR": tmp_dir}):
                self.assertEqual(get_config_dir(), Path(tmp_dir).resolve())

    def test_get_config_dir_default_uses_platformdirs(self) -> None:
        """По умолчанию используется каталог platformdirs.user_config_dir."""
        with tempfile.TemporaryDirectory() as fake_user_dir:
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("CAPRI_CONFIG_DIR", None)
                with patch(
                    "capri.core.settings.user_config_dir",
                    return_value=fake_user_dir,
                ):
                    resolved = get_config_dir()
                    self.assertEqual(resolved, Path(fake_user_dir))

    def test_get_config_dir_fallback_on_os_error(self) -> None:
        """При ошибке доступа к пользовательскому каталогу происходит откат в temp."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CAPRI_CONFIG_DIR", None)
            with patch(
                "capri.core.settings.user_config_dir",
                return_value="Z:\\NonExistent_Invalid_Path_999",
            ):
                resolved = get_config_dir()
                self.assertEqual(resolved, Path(tempfile.gettempdir()))

    def test_no_dot_capri_created_in_project_root(self) -> None:
        """В корне проекта ни при каких условиях не должна создаваться папка .capri."""
        project_root = Path(__file__).resolve().parent.parent
        dot_capri = project_root / ".capri"

        with tempfile.TemporaryDirectory() as fake_user_dir:
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("CAPRI_CONFIG_DIR", None)
                with patch(
                    "capri.core.settings.user_config_dir",
                    return_value=fake_user_dir,
                ):
                    _ = get_config_dir()
                    _ = _get_default_config_path()
                    _ = spotify.config_path()
                    manager = ConfigManager()
                    manager.save_config({"behavior": {"designated_screen": 0}})

        self.assertFalse(
            dot_capri.exists(),
            "Папка .capri была создана в корне репозитория!",
        )

    def test_spotify_config_path_delegates_to_config_dir(self) -> None:
        """Путь к spotify.json строится строго от get_config_dir()."""
        with tempfile.TemporaryDirectory() as custom_dir:
            with patch.dict(os.environ, {"CAPRI_CONFIG_DIR": custom_dir}):
                expected = Path(custom_dir).resolve() / "spotify.json"
                self.assertEqual(spotify.config_path(), expected)
