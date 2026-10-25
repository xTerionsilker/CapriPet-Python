"""Управление Spotify: поиск и воспроизведение треков.

Команда ``спотифай <запрос>`` открывает Spotify и запускает найденный трек.
Чтобы Capri умела выбирать трек сама, нужны ключи приложения Spotify
(Client ID и Client Secret из https://developer.spotify.com/dashboard):
поиск выполняется через Web API по Client Credentials, без входа в аккаунт.
Ключи читаются из переменных окружения ``SPOTIFY_CLIENT_ID`` /
``SPOTIFY_CLIENT_SECRET`` или из файла
``~/.config/capri/spotify.json``::

    {"client_id": "...", "client_secret": "..."}

Без ключей команда всё равно работает: она открывает поиск Spotify с
запросом, и нужный трек можно запустить вручную.

Воспроизведением (пауза, продолжение, следующий/предыдущий трек) Capri
управляет через MPRIS по D-Bus, поэтому Spotify должен быть запущен.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SEARCH_URL = "https://api.spotify.com/v1/search"
_HTTP_TIMEOUT = 6.0

_MPRIS_DEST = "org.mpris.MediaPlayer2.spotify"
_MPRIS_PATH = "/org/mpris/MediaPlayer2"
_MPRIS_PLAYER = "org.mpris.MediaPlayer2.Player"

# Кэш токена Web API: (значение, момент истечения по monotonic).
_token_cache: tuple[str, float] | None = None


class SpotifyError(RuntimeError):
    """Ошибка обращения к Spotify Web API."""


# --- поиск и запуск --------------------------------------------------------
def play(query: str) -> str:
    """Найти трек по запросу и запустить его в клиенте Spotify."""
    query = query.strip()
    if not query:
        return "Что включить? Скажи: «спотифай <запрос>»."

    try:
        found = _find_track(query)
    except SpotifyError as error:
        # Поиск не настроен или сервис недоступен — открываем поиск клиента.
        if _open_uri(_search_uri(query)):
            return f"Открыл поиск Spotify: {query} ({error})"
        return "Не удалось открыть Spotify. Проверьте, что клиент установлен."

    if found is not None:
        uri, title, artists = found
        if not _open_uri(uri):
            return "Не удалось открыть Spotify. Проверьте, что клиент установлен."
        return f"Включаю: {artists} — {title}" if artists else f"Включаю: {title}"

    if not _open_uri(_search_uri(query)):
        return "Не удалось открыть Spotify. Проверьте, что клиент установлен."
    return f"Ничего не нашёл. Открыл поиск Spotify: {query}"


# --- управление воспроизведением ------------------------------------------
def pause() -> str:
    if not _player_call("Pause"):
        return "Spotify не запущен."
    return "Пауза."


def resume() -> str:
    if not _player_call("Play"):
        return "Spotify не запущен."
    return "Продолжаю."


def next_track() -> str:
    if not _player_call("Next"):
        return "Spotify не запущен."
    return "Следующий трек."


def previous_track() -> str:
    if not _player_call("Previous"):
        return "Spotify не запущен."
    return "Предыдущий трек."


# --- Web API ---------------------------------------------------------------
def _find_track(query: str) -> tuple[str, str, str] | None:
    """Найти первый трек по запросу. ``None`` — если ничего не найдено."""
    credentials = _load_credentials()
    if credentials is None:
        raise SpotifyError("не настроены ключи Spotify")

    token = _access_token(*credentials)
    params = urllib.parse.urlencode(
        {"q": query, "type": "track", "limit": 1}
    )
    request = urllib.request.Request(
        f"{_SEARCH_URL}?{params}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise SpotifyError(f"Spotify ответил {error.code}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise SpotifyError("нет связи с Spotify") from error
    except json.JSONDecodeError as error:
        raise SpotifyError("некорректный ответ Spotify") from error

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
    return uri, title, artists


def _access_token(client_id: str, client_secret: str) -> str:
    global _token_cache
    now = time.monotonic()
    if _token_cache is not None and now < _token_cache[1]:
        return _token_cache[0]

    auth = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode("ascii")
    request = urllib.request.Request(
        _TOKEN_URL,
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
        with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
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


def _load_credentials() -> tuple[str, str] | None:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        return client_id, client_secret

    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    client_id = str(data.get("client_id", "")).strip()
    client_secret = str(data.get("client_secret", "")).strip()
    if client_id and client_secret:
        return client_id, client_secret
    return None


def _config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "capri" / "spotify.json"


# --- системные вызовы ------------------------------------------------------
def _search_uri(query: str) -> str:
    return "spotify:search:" + urllib.parse.quote(query.strip(), safe="")


def _open_uri(uri: str) -> bool:
    """Открыть URI через обработчик схемы по умолчанию."""
    for command in (["gio", "open", uri], ["xdg-open", uri]):
        if shutil.which(command[0]) is None:
            continue
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return True
    return False


def _player_call(method: str) -> bool:
    """Вызвать метод MPRIS-плеера Spotify."""
    if shutil.which("dbus-send") is None:
        return False
    try:
        result = subprocess.run(
            [
                "dbus-send",
                "--session",
                f"--dest={_MPRIS_DEST}",
                "--type=method_call",
                _MPRIS_PATH,
                f"{_MPRIS_PLAYER}.{method}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0
