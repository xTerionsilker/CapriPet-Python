from __future__ import annotations

from typing import Any
import webbrowser
from urllib.parse import quote_plus
import logging
from pathlib import Path
import datetime

import yt_dlp
import httpx
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

REPO_URL = "https://github.com/xTerionsilker/CapriPet-Python"
UPDATE_FILE_URL = (
    "https://raw.githubusercontent.com/xTerionsilker/CapriPet-Python/main/version.txt"
)
VERSION_FILENAME = "version.txt"
REQUEST_TIMEOUT_SEC = 5


def search_google(query: str) -> str:
    query = query.strip()
    if not query:
        return "Что искать в Google? Скажи: «гугл <запрос>»."
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Ищу в Google: {query}"


def fetch_youtube_top_videos(query: str, limit: int = 5) -> list[dict[str, str]]:
    query = query.strip()
    if not query:
        return []

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            entries = res.get("entries") or []

            videos: list[dict[str, str]] = []
            for entry in entries:
                if not entry:
                    continue
                vid = entry.get("id")
                title = entry.get("title") or ""
                url = entry.get("url") or f"https://www.youtube.com/watch?v={vid}"
                if vid:
                    videos.append({
                        "id": str(vid),
                        "title": str(title).strip(),
                        "url": str(url),
                    })
            return videos[:limit]
    except Exception as exc:
        logger.debug("Ошибка при поиске через yt-dlp: %s", exc)
        return []


def search_youtube(query: str) -> str:
    query = query.strip()
    if not query:
        return "Что искать на YouTube? Скажи: «ютуб <запрос>»."
    webbrowser.open(
        f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    )
    return f"Ищу на YouTube: {query}"


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
    webbrowser.open(REPO_URL)
    return "Открыл страницу обновления."
