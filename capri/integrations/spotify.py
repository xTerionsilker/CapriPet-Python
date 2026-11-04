from __future__ import annotations

import asyncio
import logging
import sys
import urllib.parse
import webbrowser
from typing import Any

from .spotify_api import SpotifyError, find_track

logger = logging.getLogger(__name__)

_MPRIS_DEST = "org.mpris.MediaPlayer2.spotify"
_MPRIS_PATH = "/org/mpris/MediaPlayer2"
_MPRIS_PLAYER = "org.mpris.MediaPlayer2.Player"
_MPRIS_PROPERTIES = "org.freedesktop.DBus.Properties"


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
    info = _current_track_windows() if sys.platform == "win32" else _current_track_linux()
    if not info:
        return "Сейчас ничего не играет или Spotify закрыт."

    title, artist = info
    if title and artist:
        return f"Сейчас играет: {artist} — {title}"
    if title:
        return f"Сейчас играет: {title}"
    return f"Сейчас играет: {artist}"


async def _mpris_call(member: str) -> None:
    from dbus_next import Message, MessageType
    from dbus_next.aio import MessageBus

    bus = await MessageBus().connect()
    try:
        reply = await bus.call(
            Message(
                destination=_MPRIS_DEST,
                path=_MPRIS_PATH,
                interface=_MPRIS_PLAYER,
                member=member,
            )
        )
    finally:
        bus.disconnect()

    if reply.message_type == MessageType.ERROR:
        raise RuntimeError(f"{reply.error_name}: {reply.body[0] if reply.body else ''}")


async def _mpris_property(name: str) -> Any:
    from dbus_next import Message, MessageType
    from dbus_next.aio import MessageBus

    bus = await MessageBus().connect()
    try:
        reply = await bus.call(
            Message(
                destination=_MPRIS_DEST,
                path=_MPRIS_PATH,
                interface=_MPRIS_PROPERTIES,
                member="Get",
                signature="ss",
                body=[_MPRIS_PLAYER, name],
            )
        )
    finally:
        bus.disconnect()

    if reply.message_type == MessageType.ERROR:
        raise RuntimeError(f"{reply.error_name}: {reply.body[0] if reply.body else ''}")
    return reply.body[0]


def _current_track_linux() -> tuple[str, str] | None:
    try:
        metadata = asyncio.run(_mpris_property("Metadata"))
    except Exception as error:
        logger.debug("MPRIS metadata query failed: %s", error)
        return None

    value = getattr(metadata, "value", metadata)
    if not isinstance(value, dict):
        return None

    title = _variant_value(value.get("xesam:title"), "")
    artists = _variant_value(value.get("xesam:artist"), [])
    if isinstance(artists, str):
        artists = [artists]
    artist = ", ".join(str(item) for item in artists if item)

    title = str(title).strip()
    if title or artist:
        return title, artist
    return None


def _variant_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    return getattr(value, "value", value)


def _search_uri(query: str) -> str:
    return "spotify:search:" + urllib.parse.quote(query.strip(), safe="")


def _open_uri(uri: str) -> bool:
    try:
        return bool(webbrowser.open(uri))
    except OSError:
        return False


def _current_track_windows() -> tuple[str, str] | None:
    try:
        import ctypes

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
        return _send_win_media_key(vk) if vk is not None else False

    try:
        asyncio.run(_mpris_call(method))
        return True
    except Exception as error:
        logger.debug("MPRIS %s failed: %s", method, error)
        return False
