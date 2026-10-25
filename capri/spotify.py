"""Управление Spotify: поиск и воспроизведение треков.

Команда ``спотифай <запрос>`` открывает Spotify и запускает найденный трек.
Чтобы Capri умела выбирать трек сама, нужны ключи приложения Spotify
(Client ID и Client Secret из https://developer.spotify.com/dashboard) — их
чтение, токен и сам поиск вынесены в ``capri.spotify_api``. Без ключей
команда всё равно работает: она открывает поиск Spotify с запросом, и
нужный трек можно запустить вручную.

Воспроизведением (пауза, продолжение, следующий/предыдущий трек) Capri
управляет через MPRIS по D-Bus, поэтому Spotify должен быть запущен.
"""

from __future__ import annotations

import shutil
import subprocess
import urllib.parse

from .spotify_api import SpotifyError, find_track

_MPRIS_DEST = "org.mpris.MediaPlayer2.spotify"
_MPRIS_PATH = "/org/mpris/MediaPlayer2"
_MPRIS_PLAYER = "org.mpris.MediaPlayer2.Player"


# --- поиск и запуск --------------------------------------------------------
def play(query: str) -> str:
    """Найти трек по запросу и запустить его в клиенте Spotify."""
    query = query.strip()
    if not query:
        return "Что включить? Скажи: «спотифай <запрос>»."

    try:
        found = find_track(query)
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
