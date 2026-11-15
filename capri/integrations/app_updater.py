"""Проверка обновлений приложения CapriPet через GitHub."""

from __future__ import annotations

import datetime
import logging
from pathlib import Path

import httpx
from dateutil import parser as date_parser

from .web_search import safe_open_url

logger = logging.getLogger(__name__)

REPO_URL = "https://github.com/xTerionsilker/CapriPet-Python"
UPDATE_FILE_URL = "https://raw.githubusercontent.com/xTerionsilker/CapriPet-Python/main/version.txt"
VERSION_FILENAME = "version.txt"
REQUEST_TIMEOUT_SEC = 5


def get_version_file_path() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / VERSION_FILENAME


def parse_version_datetime(raw_text: str) -> datetime.datetime | None:
    clean = raw_text.strip()
    if not clean:
        return None

    first_line = clean.splitlines()[0].strip()
    try:
        parsed = datetime.datetime.fromisoformat(first_line)
    except ValueError:
        try:
            parsed = date_parser.parse(first_line, dayfirst=True)
        except (ValueError, OverflowError):
            logger.warning("Некорректная дата/время в версии: %r", first_line)
            return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return parsed


def format_version_datetime(dt: datetime.datetime) -> str:
    if dt.second > 0:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return dt.strftime("%Y-%m-%d %H:%M")


def read_local_version_datetime() -> datetime.datetime | None:
    path = get_version_file_path()
    if not path.is_file():
        logger.warning("Локальный файл версии %s не найден", path)
        return None
    try:
        return parse_version_datetime(path.read_text(encoding="utf-8"))
    except OSError as exc:
        logger.warning("Не удалось прочитать локальный файл версии: %s", exc)
        return None


def fetch_remote_version_datetime() -> datetime.datetime | None:
    try:
        response = httpx.get(
            UPDATE_FILE_URL,
            headers={"User-Agent": "CapriPet-Updater"},
            timeout=REQUEST_TIMEOUT_SEC,
            follow_redirects=True,
        )
        response.raise_for_status()
        return parse_version_datetime(response.text)
    except httpx.HTTPError as exc:
        logger.warning("Ошибка при сетевом запросе к удалённой версии: %s", exc)
        return None


def open_update_page() -> str:
    safe_open_url(REPO_URL)
    return "Открываю страницу на GitHub. Качаем апгрейд!"
