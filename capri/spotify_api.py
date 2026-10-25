"""Клиент Spotify Web API: ключи, токен и поиск трека.

Отделён от ``capri.spotify``, который отвечает за запуск треков и
управление воспроизведением. Поиск идёт через Web API по Client
Credentials, без входа в аккаунт; ключи читаются из переменных окружения
``SPOTIFY_CLIENT_ID`` / ``SPOTIFY_CLIENT_SECRET`` или из файла
``%APPDATA%\capri\spotify.json`` (например,
``C:\Users\имя\AppData\Roaming\capri\spotify.json``)::

    {"client_id": "...", "client_secret": "..."}

Без ключей :func:`find_track` бросает :class:`SpotifyError`, а вызывающая
сторона открывает поиск Spotify с запросом вручную.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"
HTTP_TIMEOUT = 6.0

# Кэш токена Web API: (значение, момент истечения по monotonic).
_token_cache: tuple[str, float] | None = None


class SpotifyError(RuntimeError):
    """Ошибка обращения к Spotify Web API."""


def find_track(query: str) -> tuple[str, str, str] | None:
    """Найти первый трек по запросу. ``None`` — если ничего не найдено.

    Возвращает ``(uri, название, исполнители)``. Бросает
    :class:`SpotifyError`, если поиск не настроен или сервис недоступен.
    """
    credentials = load_credentials()
    if credentials is None:
        raise SpotifyError("не настроены ключи Spotify")

    token = access_token(*credentials)
    params = urllib.parse.urlencode(
        {"q": query, "type": "track", "limit": 1}
    )
    request = urllib.request.Request(
        f"{SEARCH_URL}?{params}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise SpotifyError(f"Spotify ответил {error.code}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise SpotifyError("нет связи с Spotify") from error
    except json.JSONDecodeError as error:
        raise SpotifyError("некорректный ответ Spotify") from error

    return _first_track(payload)


def access_token(client_id: str, client_secret: str) -> str:
    """Получить токен Client Credentials, кэшируя его до истечения."""
    global _token_cache
    now = time.monotonic()
    if _token_cache is not None and now < _token_cache[1]:
        return _token_cache[0]

    auth = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode("ascii")
    request = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(
            {"grant_type": "client_credentials"}
        ).encode(),
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise SpotifyError("ключи Spotify не приняты") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise SpotifyError("нет связи с Spotify") from error
    except json.JSONDecodeError as error:
        raise SpotifyError("некорректный ответ Spotify") from error

    token = payload.get("access_token")
    if not token:
        raise SpotifyError("Spotify не выдал токен")
    expires_in = int(payload.get("expires_in", 3600))
    # Небольшой запас, чтобы не использовать токен в последнюю секунду.
    _token_cache = (str(token), now + max(60, expires_in - 60))
    return str(token)


def load_credentials() -> tuple[str, str] | None:
    """Прочитать ключи приложения из окружения или файла настроек."""
    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        return client_id, client_secret

    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    client_id = str(data.get("client_id", "")).strip()
    client_secret = str(data.get("client_secret", "")).strip()
    if client_id and client_secret:
        return client_id, client_secret
    return None


def config_path() -> Path:
    r"""Путь к файлу с ключами ``%APPDATA%\capri\spotify.json``.

    В Linux Capri читала ``XDG_CONFIG_HOME``; в Windows штатное место
    пользовательских настроек — каталог ``%APPDATA%`` (переменная
    ``APPDATA`` в окружении).
    """
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "capri" / "spotify.json"


# --- внутреннее ------------------------------------------------------------
def _first_track(payload: dict) -> tuple[str, str, str] | None:
    """Достать из ответа поиска ``(uri, название, исполнители)``."""
    items = (payload.get("tracks") or {}).get("items") or []
    if not items:
        return None
    track = items[0]
    uri = track.get("uri")
    if not uri:
        return None
    title = track.get("name") or "без названия"
    artists = ", ".join(
        artist.get("name", "")
        for artist in track.get("artists") or ()
        if artist.get("name")
    )
    return str(uri), title, artists
