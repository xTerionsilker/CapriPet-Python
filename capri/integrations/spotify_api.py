from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path

import httpx

TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"
HTTP_TIMEOUT = 6.0

_token_cache: tuple[str, float] | None = None


class SpotifyError(RuntimeError):
    pass

def find_track(query: str) -> tuple[str, str, str] | None:
    credentials = load_credentials()
    if credentials is None:
        raise SpotifyError("не настроены ключи Spotify")

    token = access_token(*credentials)
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": query, "type": "track", "limit": "1"}

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            response = client.get(SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as error:
        raise SpotifyError(f"Spotify ответил {error.response.status_code}") from error
    except httpx.RequestError as error:
        raise SpotifyError("нет связи с Spotify") from error
    except json.JSONDecodeError as error:
        raise SpotifyError("некорректный ответ Spotify") from error

    return _first_track(payload)


def access_token(client_id: str, client_secret: str) -> str:
    global _token_cache
    now = time.monotonic()
    if _token_cache is not None and now < _token_cache[1]:
        return _token_cache[0]

    auth = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode("ascii")
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            response = client.post(TOKEN_URL, data=data, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as error:
        raise SpotifyError("ключи Spotify не приняты") from error
    except httpx.RequestError as error:
        raise SpotifyError("нет связи с Spotify") from error
    except json.JSONDecodeError as error:
        raise SpotifyError("некорректный ответ Spotify") from error

    token = payload.get("access_token")
    if not token:
        raise SpotifyError("Spotify не выдал токен")
    expires_in = int(payload.get("expires_in", 3600))
    _token_cache = (str(token), now + max(60, expires_in - 60))
    return str(token)


def load_credentials() -> tuple[str, str] | None:
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

    project_root = Path(__file__).resolve().parent.parent.parent
    local_spotify = project_root / ".capri" / "spotify.json"
    if local_spotify.is_file():
        return local_spotify


    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
    system_spotify = base / "capri" / "spotify.json"
    if system_spotify.is_file():
        return system_spotify


    local_dir = project_root / ".capri"
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        return local_spotify
    except OSError:
        return system_spotify


def _first_track(payload: dict) -> tuple[str, str, str] | None:
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
