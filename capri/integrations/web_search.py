from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus


def search_google(query: str) -> str:
    """Выполняет поиск в Google через браузер по умолчанию."""
    query = query.strip()
    if not query:
        return "Что искать в Google? Скажи: «гугл <запрос>»."
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Ищу в Google: {query}"


def search_youtube(query: str) -> str:
    """Выполняет поиск на YouTube через браузер по умолчанию."""
    query = query.strip()
    if not query:
        return "Что искать на YouTube? Скажи: «ютуб <запрос>»."
    webbrowser.open(
        f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    )
    return f"Ищу на YouTube: {query}"
