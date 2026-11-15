"""Веб-поиск в Google и YouTube для CapriPet."""

from __future__ import annotations

import logging
import webbrowser
from urllib.parse import quote_plus, urlsplit

import yt_dlp

logger = logging.getLogger(__name__)

ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https"})


def safe_open_url(url: str) -> bool:
    """Безопасно открывает URL в браузере только по разрешенным веб-схемам."""
    if not url or not isinstance(url, str):
        return False

    clean_url = url.strip()
    try:
        parsed = urlsplit(clean_url)
        if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
            logger.warning(
                "Заблокирована попытка открытия URL с неподдерживаемой схемой: %r",
                parsed.scheme,
            )
            return False
        if not parsed.netloc:
            logger.warning(
                "Заблокирован некорректный URL без хоста: %s", clean_url
            )
            return False
        return bool(webbrowser.open(clean_url))
    except Exception as e:  # noqa: BLE001
        logger.warning("Ошибка при открытии URL %s: %s", clean_url, e)
        return False


def search_google(query: str) -> str:
    query = query.strip()
    if not query:
        return "Чё нарыть в Сети? Давай команду: «гугл <запрос>»!"
    safe_open_url(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Запускаю сетевых пауков по запросу: {query}!"


def fetch_youtube_top_videos(
    query: str, limit: int = 5
) -> list[dict[str, str]]:
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
            res = ydl.extract_info(
                f"ytsearch{limit}:{query}", download=False
            )
            entries = res.get("entries") or []

            videos: list[dict[str, str]] = []
            for entry in entries:
                if not entry:
                    continue
                vid = entry.get("id")
                title = entry.get("title") or ""
                url = (
                    entry.get("url")
                    or f"https://www.youtube.com/watch?v={vid}"
                )
                if vid:
                    videos.append(
                        {
                            "id": str(vid),
                            "title": str(title).strip(),
                            "url": str(url),
                        }
                    )
            return videos[:limit]
    except Exception as exc:  # noqa: BLE001
        logger.debug("Ошибка при поиске через yt-dlp: %s", exc)
        return []


def search_youtube(query: str) -> str:
    query = query.strip()
    if not query:
        return "Что искать на YouTube? Скажи: «ютуб <запрос>»."
    safe_open_url(
        f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    )
    return f"Ищу на YouTube: {query}"






