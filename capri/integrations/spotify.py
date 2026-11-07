"""Интеграция со Spotify: веб-поиск треков и управление локальным плеером.

Модуль выполняет поиск композиций через Spotify Web API (Spotipy) и управляет
воспроизведением локального десктопного клиента Windows через Win32 API
(сообщения WM_APPCOMMAND).
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import urllib.parse
import webbrowser
from pathlib import Path

import psutil
import spotipy
from platformdirs import user_config_dir
from requests import RequestException
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 6.0
_PAUSED_TITLES = {"spotify", "spotify free", "spotify premium"}
_CMD_PLAY_PAUSE = 14
_CMD_NEXT = 11
_CMD_PREV = 12

class SpotifyState:
    """Хранилище изменяемого состояния сессии и кэша клиента Spotify."""

    def __init__(self) -> None:
        self.client_cache: tuple[tuple[str, str], spotipy.Spotify] | None = None
        self.last_known_state: str = "unknown"

    def get_client(
        self, credentials: tuple[str, str]
    ) -> spotipy.Spotify | None:
        if (
            self.client_cache is not None
            and self.client_cache[0] == credentials
        ):
            return self.client_cache[1]
        return None

    def set_client(
        self, credentials: tuple[str, str], client: spotipy.Spotify
    ) -> None:
        self.client_cache = (credentials, client)


_state = SpotifyState()


class SpotifyError(RuntimeError):
    """Исключение, возникающее при ошибках взаимодействия со Spotify."""


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
    client = _state.get_client(credentials)
    if client is not None:
        return client

    client_id, client_secret = credentials
    manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )
    client = spotipy.Spotify(
        client_credentials_manager=manager,
        requests_timeout=HTTP_TIMEOUT,
    )
    _state.set_client(credentials, client)
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


def _get_spotify_pids() -> set[int]:
    pids: set[int] = set()
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        try:
            name = proc.info["name"]
            if name and name.lower() == "spotify.exe":
                pids.add(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids


def _find_spotify_windows(pids: set[int]) -> list[int]:
    if not pids:
        return []

    user32 = ctypes.windll.user32
    hwnds: list[int] = []

    def enum_cb(hwnd: int, _extra: int) -> bool:
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            class_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_buf, 256)
            if class_buf.value in (
                "Chrome_WidgetWin_0",
                "Chrome_WidgetWin_1",
            ):
                hwnds.append(hwnd)
        return True

    cb = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
    )(enum_cb)
    user32.EnumWindows(cb, 0)
    return hwnds


def _get_spotify_title(pids: set[int]) -> str:
    user32 = ctypes.windll.user32
    titles: list[str] = []

    def enum_cb(hwnd: int, _extra: int) -> bool:
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                text = buff.value.strip()
                if text:
                    titles.append(text)
        return True

    cb = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
    )(enum_cb)
    user32.EnumWindows(cb, 0)

    for t in titles:
        if t.lower() not in _PAUSED_TITLES and (" — " in t or " - " in t):
            return t
    for t in titles:
        if t:
            return t
    return ""


def _send_spotify_command(cmd: int) -> bool:
    pids = _get_spotify_pids()
    if not pids:
        return False

    hwnds = _find_spotify_windows(pids)
    if not hwnds:
        return False

    user32 = ctypes.windll.user32
    lparam = cmd << 16
    success = False
    for hwnd in hwnds:
        try:
            result = ctypes.c_size_t()
            if user32.SendMessageTimeoutW(
                hwnd, 0x0319, 0, lparam, 2, 150, ctypes.byref(result)
            ) or user32.PostMessageW(hwnd, 0x0319, 0, lparam):
                success = True
        except Exception:
            continue
    return success


def play(query: str) -> str:
    query = query.strip()
    if not query:
        return "Что включить? Скажи: «спотифай <запрос>»!"

    try:
        found = find_track(query)
    except SpotifyError as error:
        if _open_uri(_search_uri(query)):
            return f"Открыла поиск Spotify: {query} ({error})"
        return (
            "Не удалось открыть Spotify. Проверь, что клиент вообще установлен!"
        )

    if found is not None:
        uri, title, artists = found
        if not _open_uri(uri):
            return "Не удалось открыть Spotify. Проверь, что клиент установлен!"
        _state.last_known_state = "playing"
        return (
            f"Врубаю бит: {artists} — {title}!"
            if artists
            else f"Врубаю трек: {title}!"
        )

    if not _open_uri(_search_uri(query)):
        return (
            "Не удалось открыть Spotify. Проверь, что клиент установлен!"
        )
    return f"Ничего не нашла в библиотеке. Открыла поиск в Spotify: {query}"


def pause() -> str:
    pids = _get_spotify_pids()
    if not pids:
        _state.last_known_state = "unknown"
        return "Сначала запусти Spotify, а потом требуй саундтрек!"

    title = _get_spotify_title(pids)
    if (
        title
        and title.lower() not in _PAUSED_TITLES
        and (" — " in title or " - " in title)
    ):
        _state.last_known_state = "playing"

    if _state.last_known_state == "paused":
        return "Да и так тишина стоит, куда ещё глушить?"

    if not _send_spotify_command(_CMD_PLAY_PAUSE):
        return "Не вышло приглушить музыку. Плеер не отзывается!"

    _state.last_known_state = "paused"
    return "Глушу звук!"


def resume() -> str:
    pids = _get_spotify_pids()
    if not pids:
        _state.last_known_state = "unknown"
        return "Spotify даже не запущен, хост!"

    title = _get_spotify_title(pids)
    if (
        title
        and title.lower() not in _PAUSED_TITLES
        and (" — " in title or " - " in title)
    ):
        _state.last_known_state = "playing"

    if _state.last_known_state == "playing":
        return "Уши протри, и так же на всю катушку играет!"

    if not _send_spotify_command(_CMD_PLAY_PAUSE):
        return "Не вышло возобновить трек!"

    _state.last_known_state = "playing"
    return "Врубаю бит обратно!"


def next_track() -> str:
    if not _send_spotify_command(_CMD_NEXT):
        _state.last_known_state = "unknown"
        return "Spotify не запущен, переключать нечего!"
    _state.last_known_state = "playing"
    return "Скипаю этот трек!"


def previous_track() -> str:
    if not _send_spotify_command(_CMD_PREV):
        _state.last_known_state = "unknown"
        return "Spotify не запущен!"
    _state.last_known_state = "playing"
    return "Мотаем назад, лови!"


def current_track() -> str:
    pids = _get_spotify_pids()
    if not pids:
        return "Spotify закрыт."

    title = _get_spotify_title(pids)
    if not title:
        return "Сейчас ничего не играет или Spotify на паузе."

    delimiter = (
        " — " if " — " in title else (" - " if " - " in title else None)
    )
    if delimiter and title.lower() not in _PAUSED_TITLES:
        parts = title.split(delimiter, 1)
        artist = parts[0].strip()
        track = parts[1].strip()
        if artist and track:
            return f"Сейчас играет: {artist} — {track}"
        if track:
            return f"Сейчас играет: {track}"
        return f"Сейчас играет: {artist}"

    if _state.last_known_state == "paused":
        return "Spotify сейчас на паузе."
    return "Spotify запущен."


def _search_uri(query: str) -> str:
    return "spotify:search:" + urllib.parse.quote(query.strip(), safe="")


def _open_uri(uri: str) -> bool:
    try:
        return bool(webbrowser.open(uri))
    except OSError:
        return False


class SpotifyManager:
    """Менеджер для управления воспроизведением и поиском музыки в Spotify.

    Предоставляет унифицированный объектный интерфейс к операциям поиска
    композиций, запуска воспроизведения и управления плеером Spotify.
    """

    @staticmethod
    def find_track(query: str) -> tuple[str, str, str] | None:
        return find_track(query)

    @staticmethod
    def play(query: str) -> str:
        return play(query)

    @staticmethod
    def pause() -> str:
        return pause()

    @staticmethod
    def resume() -> str:
        return resume()

    @staticmethod
    def next_track() -> str:
        return next_track()

    @staticmethod
    def previous_track() -> str:
        return previous_track()

    @staticmethod
    def current_track() -> str:
        return current_track()
