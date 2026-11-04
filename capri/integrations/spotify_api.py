from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import spotipy
from platformdirs import user_config_dir
from requests import RequestException
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 6.0

_client_cache: tuple[tuple[str, str], spotipy.Spotify] | None = None


class SpotifyError(RuntimeError):
    pass


def find_track(query: str) -> tuple[str, str, str] | None:
    credentials = load_credentials()
    if credentials is None:
        raise SpotifyError("не настроены ключи Spotify")

    client = _spotify_client(credentials)
    try:
        payload = client.search(q=query, type="track", limit=1)
    except SpotifyException as error:
        status = error.http_status
        if status in (401, 403):
            raise SpotifyError("ключи Spotify не приняты") from error
        raise SpotifyError(f"Spotify ответил {status}") from error
    except RequestException as error:
        raise SpotifyError("нет связи с Spotify") from error

    return _first_track(payload)


def _spotify_client(credentials: tuple[str, str]) -> spotipy.Spotify:
    global _client_cache
    if _client_cache is not None and _client_cache[0] == credentials:
        return _client_cache[1]

    client_id, client_secret = credentials
    manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )
    client = spotipy.Spotify(
        client_credentials_manager=manager,
        requests_timeout=HTTP_TIMEOUT,
    )
    _client_cache = (credentials, client)
    return client


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

    system_spotify = Path(user_config_dir("capri")) / "spotify.json"
    if system_spotify.is_file():
        return system_spotify

    local_dir = project_root / ".capri"
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        return local_spotify
    except OSError:
        system_spotify.parent.mkdir(parents=True, exist_ok=True)
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
    return str(uri), str(title), artists
