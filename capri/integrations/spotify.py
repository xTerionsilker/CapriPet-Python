from __future__ import annotations

import ctypes
import logging
import urllib.parse
import webbrowser

from .spotify_api import SpotifyError, find_track

logger = logging.getLogger(__name__)


def play(query: str) -> str:
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
        return f"Включаю: {artists} — {title}" if artists else f"Включаю: {title}"

    if not _open_uri(_search_uri(query)):
        return "Не удалось открыть Spotify. Проверьте, что клиент установлен."
    return f"Ничего не нашёл. Открыл поиск Spotify: {query}"


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


def current_track() -> str:
    info = _current_track_windows()
    if not info:
        return "Сейчас ничего не играет или Spotify закрыт."

    title, artist = info
    if title and artist:
        return f"Сейчас играет: {artist} — {title}"
    if title:
        return f"Сейчас играет: {title}"
    return f"Сейчас играет: {artist}"


def _search_uri(query: str) -> str:
    return "spotify:search:" + urllib.parse.quote(query.strip(), safe="")


def _open_uri(uri: str) -> bool:
    try:
        return bool(webbrowser.open(uri))
    except OSError:
        return False


def _current_track_windows() -> tuple[str, str] | None:
    try:
        user32 = ctypes.windll.user32
        titles: list[tuple[str, str]] = []

        wnd_enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_cb(hwnd: ctypes.c_void_p, _extra: ctypes.c_void_p) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                text = buff.value.strip()

                class_buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_buf, 256)
                cls_name = class_buf.value
                if "Spotify" in cls_name or "Spotify" in text or " — " in text or " - " in text:
                    titles.append((cls_name, text))
            return True

        user32.EnumWindows(wnd_enum_proc(enum_cb), 0)

        for cls_name, text in titles:
            if cls_name == "Chrome_WidgetWin_0" and text and text not in (
                "Spotify",
                "Spotify Free",
                "Spotify Premium",
            ):
                delimiter = " — " if " — " in text else (" - " if " - " in text else None)
                if delimiter:
                    parts = text.split(delimiter, 1)
                    return parts[1].strip(), parts[0].strip()
                return text, ""
    except Exception:
        pass
    return None


def _send_win_media_key(vk_code: int) -> bool:
    try:
        keybd_event = ctypes.windll.user32.keybd_event
        keybd_event(vk_code, 0, 1, 0)
        keybd_event(vk_code, 0, 1 | 2, 0)
        return True
    except Exception:
        return False


def _player_call(method: str) -> bool:
    key_map = {
        "Play": 0xB3,
        "Pause": 0xB3,
        "PlayPause": 0xB3,
        "Next": 0xB0,
        "Previous": 0xB1,
    }
    vk = key_map.get(method)
    return _send_win_media_key(vk) if vk is not None else False
