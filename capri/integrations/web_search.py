from __future__ import annotations

import logging
from typing import Any
import webbrowser
from urllib.parse import quote_plus

import yt_dlp

logger = logging.getLogger(__name__)


def search_google(query: str) -> str:
    """Выполняет поиск в Google через браузер по умолчанию."""
    query = query.strip()
    if not query:
        return "Что искать в Google? Скажи: «гугл <запрос>»."
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Ищу в Google: {query}"


def fetch_youtube_top_videos(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Получает топ-видео с YouTube по поисковому запросу через yt-dlp."""
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
        logger.debug("Ошибка поиска видео через yt-dlp: %s", exc)
        return []


def search_youtube(query: str) -> str:
    """Выполняет поиск на YouTube через браузер по умолчанию."""
    query = query.strip()
    if not query:
        return "Что искать на YouTube? Скажи: «ютуб <запрос>»."
    webbrowser.open(
        f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    )
    return f"Ищу на YouTube: {query}"


def open_update_page() -> str:
    """Открывает страницу репозитория проекта на GitHub в браузере по умолчанию."""
    url = "https://github.com/xTerionsilker/CapriPet-Python"
    webbrowser.open(url)
    return "Открываю страницу обновлений."

