from __future__ import annotations

import ctypes
import logging
import urllib.parse
import webbrowser

import psutil

from .spotify_api import SpotifyError, find_track

logger = logging.getLogger(__name__)

_PAUSED_TITLES = {"spotify", "spotify free", "spotify premium"}
_CMD_PLAY_PAUSE = 14
_CMD_NEXT = 11
_CMD_PREV = 12

_last_known_state: str = "unknown"


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
            if class_buf.value in ("Chrome_WidgetWin_0", "Chrome_WidgetWin_1"):
                hwnds.append(hwnd)
        return True

    cb = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum_cb)
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

    cb = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum_cb)
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
            if user32.SendMessageTimeoutW(hwnd, 0x0319, 0, lparam, 2, 150, ctypes.byref(result)):
                success = True
            elif user32.PostMessageW(hwnd, 0x0319, 0, lparam):
                success = True
        except Exception:
            continue
    return success


def play(query: str) -> str:
    global _last_known_state
    query = query.strip()
    if not query:
        return "Что включить? Скажи: «спотифай <запрос>»."

    try:
        found = find_track(query)
    except SpotifyError as error:
        if _open_uri(_search_uri(query)):
            return f"Открыл поиск Spotify: {query} ({error})"
        return "Не удалось открыть Spotify. Проверьте, что клиент установлен."

    if found is not None:
        uri, title, artists = found
        if not _open_uri(uri):
            return "Не удалось открыть Spotify. Проверьте, что клиент установлен."
        _last_known_state = "playing"
        return f"Включаю: {artists} — {title}" if artists else f"Включаю: {title}"

    if not _open_uri(_search_uri(query)):
        return "Не удалось открыть Spotify. Проверьте, что клиент установлен."
    return f"Ничего не нашёл. Открыл поиск Spotify: {query}"


def pause() -> str:
    global _last_known_state
    pids = _get_spotify_pids()
    if not pids:
        _last_known_state = "unknown"
        return "Spotify не запущен."

    title = _get_spotify_title(pids)
    if title and title.lower() not in _PAUSED_TITLES and (" — " in title or " - " in title):
        _last_known_state = "playing"

    if _last_known_state == "paused":
        return "Spotify уже на паузе."

    if not _send_spotify_command(_CMD_PLAY_PAUSE):
        return "Не удалось поставить Spotify на паузу."

    _last_known_state = "paused"
    return "Пауза."


def resume() -> str:
    global _last_known_state
    pids = _get_spotify_pids()
    if not pids:
        _last_known_state = "unknown"
        return "Spotify не запущен."

    title = _get_spotify_title(pids)
    if title and title.lower() not in _PAUSED_TITLES and (" — " in title or " - " in title):
        _last_known_state = "playing"

    if _last_known_state == "playing":
        return "Spotify уже играет."

    if not _send_spotify_command(_CMD_PLAY_PAUSE):
        return "Не удалось продолжить воспроизведение."

    _last_known_state = "playing"
    return "Продолжаю."


def next_track() -> str:
    global _last_known_state
    if not _send_spotify_command(_CMD_NEXT):
        _last_known_state = "unknown"
        return "Spotify не запущен."
    _last_known_state = "playing"
    return "Следующий трек."


def previous_track() -> str:
    global _last_known_state
    if not _send_spotify_command(_CMD_PREV):
        _last_known_state = "unknown"
        return "Spotify не запущен."
    _last_known_state = "playing"
    return "Предыдущий трек."


def current_track() -> str:
    pids = _get_spotify_pids()
    if not pids:
        return "Spotify закрыт."

    title = _get_spotify_title(pids)
    if not title:
        return "Сейчас ничего не играет или Spotify на паузе."

    delimiter = " — " if " — " in title else (" - " if " - " in title else None)
    if delimiter and title.lower() not in _PAUSED_TITLES:
        parts = title.split(delimiter, 1)
        artist = parts[0].strip()
        track = parts[1].strip()
        if artist and track:
            return f"Сейчас играет: {artist} — {track}"
        if track:
            return f"Сейчас играет: {track}"
        return f"Сейчас играет: {artist}"

    if _last_known_state == "paused":
        return "Spotify сейчас на паузе."
    return "Spotify запущен."


def _search_uri(query: str) -> str:
    return "spotify:search:" + urllib.parse.quote(query.strip(), safe="")


def _open_uri(uri: str) -> bool:
    try:
        return bool(webbrowser.open(uri))
    except OSError:
        return False
