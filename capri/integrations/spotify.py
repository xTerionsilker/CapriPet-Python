from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.parse

from .spotify_api import SpotifyError, find_track

_MPRIS_DEST = "org.mpris.MediaPlayer2.spotify"
_MPRIS_PATH = "/org/mpris/MediaPlayer2"
_MPRIS_PLAYER = "org.mpris.MediaPlayer2.Player"


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


def _search_uri(query: str) -> str:
    return "spotify:search:" + urllib.parse.quote(query.strip(), safe="")


def _open_uri(uri: str) -> bool:
    if sys.platform == "win32":
        try:
            os.startfile(uri)
            return True
        except OSError:
            pass

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


def _send_win_media_key(vk_code: int) -> bool:
    try:
        import ctypes

        keybd_event = ctypes.windll.user32.keybd_event
        # KEYEVENTF_EXTENDEDKEY = 0x0001, KEYEVENTF_KEYUP = 0x0002
        keybd_event(vk_code, 0, 1, 0)
        keybd_event(vk_code, 0, 1 | 2, 0)
        return True
    except Exception:
        return False


def _player_call(method: str) -> bool:
    if sys.platform == "win32":
        # Windows Virtual-Key Codes для мультимедиа:
        # VK_MEDIA_NEXT_TRACK = 0xB0, VK_MEDIA_PREV_TRACK = 0xB1, VK_MEDIA_PLAY_PAUSE = 0xB3
        key_map = {
            "Play": 0xB3,
            "Pause": 0xB3,
            "PlayPause": 0xB3,
            "Next": 0xB0,
            "Previous": 0xB1,
        }
        vk = key_map.get(method)
        if vk is not None:
            return _send_win_media_key(vk)
        return False

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
