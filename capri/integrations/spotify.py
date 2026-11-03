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


def current_track() -> str:
    """Возвращает информацию о текущем воспроизводимом треке."""
    if sys.platform == "win32":
        info = _current_track_windows()
    else:
        info = _current_track_linux()

    if not info:
        return "Сейчас ничего не играет или Spotify закрыт."

    title, artist = info
    if title and artist:
        return f"Сейчас играет: {artist} — {title}"
    if title:
        return f"Сейчас играет: {title}"
    return f"Сейчас играет: {artist}"


def _current_track_windows() -> tuple[str, str] | None:
    try:
        import ctypes

        user32 = ctypes.windll.user32
        titles: list[str] = []


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
            if cls_name == "Chrome_WidgetWin_0" and text and text != "Spotify" and text != "Spotify Free" and text != "Spotify Premium":

                delimiter = " — " if " — " in text else (" - " if " - " in text else None)
                if delimiter:
                    parts = text.split(delimiter, 1)
                    return parts[1].strip(), parts[0].strip()
                return text, ""
    except Exception:
        pass
    return None


def _current_track_linux() -> tuple[str, str] | None:

    if shutil.which("playerctl") is not None:
        try:
            res = subprocess.run(
                ["playerctl", "-p", "spotify", "metadata", "--format", "{{artist}}///{{title}}"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split("///", 1)
                artist = parts[0].strip()
                title = parts[1].strip() if len(parts) > 1 else ""
                if title or artist:
                    return title, artist
        except (OSError, subprocess.TimeoutExpired):
            pass


    if shutil.which("dbus-send") is not None:
        try:
            res = subprocess.run(
                [
                    "dbus-send",
                    "--session",
                    "--print-reply",
                    f"--dest={_MPRIS_DEST}",
                    _MPRIS_PATH,
                    "org.freedesktop.DBus.Properties.Get",
                    f"string:{_MPRIS_PLAYER}",
                    "string:Metadata",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout:
                return _parse_mpris_metadata(res.stdout)
        except (OSError, subprocess.TimeoutExpired):
            pass

    return None


def _parse_mpris_metadata(output: str) -> tuple[str, str] | None:
    import re

    title_match = re.search(r'string\s+"xesam:title"\s+variant\s+string\s+"([^"]+)"', output)
    title = title_match.group(1).strip() if title_match else ""

    artists: list[str] = []
    artist_section = re.search(r'string\s+"xesam:artist"\s+variant\s+array\s+\[(.*?)\]', output, re.DOTALL)
    if artist_section:
        artists = re.findall(r'string\s+"([^"]+)"', artist_section.group(1))
    artist = ", ".join(artists).strip()

    if title or artist:
        return title, artist
    return None


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

        keybd_event(vk_code, 0, 1, 0)
        keybd_event(vk_code, 0, 1 | 2, 0)
        return True
    except Exception:
        return False


def _player_call(method: str) -> bool:
    if sys.platform == "win32":


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
