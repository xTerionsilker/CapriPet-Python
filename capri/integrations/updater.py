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


_FALLBACK_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y",
)


def parse_version_datetime(raw_text: str) -> datetime.datetime | None:
    """Парсит дату и время версии (поддерживает форматы с датой и временем или только дату)."""
    clean = raw_text.strip()
    if not clean:
        return None
    # Берём первую строку на случай комментариев или доп. данных
    first_line = clean.splitlines()[0].strip()
    try:
        dt = datetime.datetime.fromisoformat(first_line)
        if dt.tzinfo is not None:
            # Приводим к наивному UTC времени для корректного сравнения
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        pass

    for fmt in _FALLBACK_DATETIME_FORMATS:
        try:
            return datetime.datetime.strptime(first_line, fmt)
        except ValueError:
            pass

    logger.warning("Некорректный формат даты/времени в версии: %r", first_line)
    return None


def format_version_datetime(dt: datetime.datetime) -> str:
    """Форматирует дату/время для отображения пользователю."""
    if dt.second > 0:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return dt.strftime("%Y-%m-%d %H:%M")


def read_local_version_datetime() -> datetime.datetime | None:
    """Считывает локальную дату и время обновления из version.txt."""
    path = get_version_file_path()
    if not path.is_file():
        logger.warning("Локальный файл версий %s не найден", path)
        return None
    try:
        content = path.read_text(encoding="utf-8").strip()
        return parse_version_datetime(content)
    except Exception as exc:
        logger.warning("Не удалось прочитать локальный файл версии: %s", exc)
        return None


def fetch_remote_version_datetime() -> datetime.datetime | None:
    """Загружает содержимое version.txt с удалённого репозитория GitHub."""
    req = urllib.request.Request(
        UPDATE_FILE_URL,
        headers={"User-Agent": "CapriPet-Updater"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
            raw = resp.read().decode("utf-8", errors="replace").strip()
            return parse_version_datetime(raw)
    except Exception as exc:
        logger.warning("Ошибка при загрузке версии из удалённого репозитория: %s", exc)
        return None


# Алиасы для обратной совместимости
read_local_version_date = read_local_version_datetime
fetch_remote_version_date = fetch_remote_version_datetime
parse_version_date = parse_version_datetime


def open_update_page() -> str:
    """Открывает страницу репозитория проекта на GitHub в браузере по умолчанию."""
    webbrowser.open(REPO_URL)
    return "Открываю страницу обновлений."
