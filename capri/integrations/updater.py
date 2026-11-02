"""Модуль проверки обновлений CapriPet через GitHub."""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
import urllib.request
import webbrowser

logger = logging.getLogger(__name__)

REPO_URL = "https://github.com/xTerionsilker/CapriPet-Python"
UPDATE_FILE_URL = (
    "https://raw.githubusercontent.com/xTerionsilker/CapriPet-Python/main/version.txt"
)
VERSION_FILENAME = "version.txt"
REQUEST_TIMEOUT_SEC = 5


def get_version_file_path() -> Path:
    """Возвращает путь к локальному файлу version.txt в корне проекта."""
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / VERSION_FILENAME


def read_local_version_date() -> datetime.date | None:
    """Считывает локальную дату обновления из version.txt."""
    path = get_version_file_path()
    if not path.is_file():
        logger.warning("Локальный файл версий %s не найден", path)
        return None
    try:
        content = path.read_text(encoding="utf-8").strip()
        return parse_version_date(content)
    except Exception as exc:
        logger.warning("Не удалось прочитать локальный файл версии: %s", exc)
        return None


def fetch_remote_version_date() -> datetime.date | None:
    """Загружает содержимое version.txt с удалённого репозитория GitHub."""
    req = urllib.request.Request(
        UPDATE_FILE_URL,
        headers={"User-Agent": "CapriPet-Updater"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
            raw = resp.read().decode("utf-8", errors="replace").strip()
            return parse_version_date(raw)
    except Exception as exc:
        logger.warning("Ошибка при загрузке версии из удалённого репозитория: %s", exc)
        return None


def parse_version_date(raw_text: str) -> datetime.date | None:
    """Парсит дату в формате YYYY-MM-DD (или первой подходящей строки)."""
    clean = raw_text.strip()
    if not clean:
        return None
    # Берём первую строку на случай комментариев или доп. данных
    first_line = clean.splitlines()[0].strip()
    try:
        return datetime.date.fromisoformat(first_line)
    except ValueError:
        logger.warning("Некорректный формат даты в версии: %r", first_line)
        return None


def open_update_page() -> str:
    """Открывает страницу репозитория проекта на GitHub в браузере по умолчанию."""
    webbrowser.open(REPO_URL)
    return "Открываю страницу обновлений."
