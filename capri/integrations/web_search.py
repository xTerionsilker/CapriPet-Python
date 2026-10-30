from __future__ import annotations

import json
import re
from typing import Any
import webbrowser
from urllib.parse import quote_plus

import requests


def search_google(query: str) -> str:
    """Выполняет поиск в Google через браузер по умолчанию."""
    query = query.strip()
    if not query:
        return "Что искать в Google? Скажи: «гугл <запрос>»."
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Ищу в Google: {query}"


def fetch_youtube_top_videos(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Получает топ-видео с YouTube по поисковому запросу."""
    query = query.strip()
    if not query:
        return []
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        resp = requests.get(
            "https://www.youtube.com/results",
            params={"search_query": query},
            headers=headers,
            timeout=5,
        )
        if resp.status_code != 200:
            return []
        match = re.search(r"var ytInitialData = ({.*?});</script>", resp.text)
        if not match:
            return []
        data = json.loads(match.group(1))

        videos: list[dict[str, str]] = []

        def extract(obj: Any) -> None:
            if isinstance(obj, dict):
                if "videoRenderer" in obj:
                    vr = obj["videoRenderer"]
                    vid = vr.get("videoId")
                    title = ""
                    if "title" in vr and "runs" in vr["title"]:
                        title = "".join(
                            run.get("text", "") for run in vr["title"]["runs"]
                        )
                    elif "title" in vr and "simpleText" in vr["title"]:
                        title = vr["title"]["simpleText"]
                    if vid and title and not any(v["id"] == vid for v in videos):
                        videos.append(
                            {
                                "id": str(vid),
                                "title": str(title).strip(),
                                "url": f"https://www.youtube.com/watch?v={vid}",
                            }
                        )
                for v in obj.values():
                    extract(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract(item)

        extract(data)
        return videos[:limit]
    except Exception:
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

