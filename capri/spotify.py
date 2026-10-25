"""Управление Spotify: поиск и воспроизведение треков (Windows 11).

Команда ``спотифай <запрос>`` открывает Spotify и запускает найденный трек.
Чтобы Capri умела выбирать трек сама, нужны ключи приложения Spotify
(Client ID и Client Secret из https://developer.spotify.com/dashboard) — их
чтение, токен и сам поиск вынесены в ``capri.spotify_api``. Без ключей
команда всё равно работает: она открывает поиск Spotify с запросом, и
нужный трек можно запустить вручную.

В Linux воспроизведением Capri управляла через MPRIS по D-Bus. В Windows
его нет, поэтому используются два штатных механизма:

* **Web Remote API** локального десктопного клиента Spotify — HTTP-сервер на
  ``127.0.0.1:8020–8022``, принимающий ``PUT /remote/control/<метод>`` без
  авторизации; работает даже со свёрнутым клиентом;
* **системные мультимедийные клавиши** (``MEDIA_PLAY_PAUSE``,
  ``MEDIA_NEXT_TRACK``, ``MEDIA_PREV_TRACK`` через ``keybd_event``) —
  запасной путь, доставляющий событие любому активному плееру.

URI вида ``spotify:track:…`` и ``spotify:search:…`` открываются стандартным
обработчиком схем Windows — ``os.startfile`` (тот же ShellExecute).
"""

from __future__ import annotations

import ctypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from .spotify_api import SpotifyError, find_track

#: Мультимедийные виртуальные клавиши Windows.
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

_KEYEVENTF_EXTENDEDKEY = 0x0001
_KEYEVENTF_KEYUP = 0x0002

#: Порты Web Remote API десктопного клиента (в порядке приоритета).
WEB_REMOTE_PORTS = (8022, 8021, 8020)

#: Сколько секунд ждать ответ локального HTTP-сервера клиента.
WEB_REMOTE_TIMEOUT_S = 1.5


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
    if _web_remote("pause") or _media_key(VK_MEDIA_PLAY_PAUSE):
        return "Пауза."
    return "Spotify не запущен."


def resume() -> str:
    if _web_remote("resume") or _media_key(VK_MEDIA_PLAY_PAUSE):
        return "Продолжаю."
    return "Spotify не запущен."


def next_track() -> str:
    if _web_remote("next") or _media_key(VK_MEDIA_NEXT_TRACK):
        return "Следующий трек."
    return "Spotify не запущен."


def previous_track() -> str:
    if _web_remote("previous") or _media_key(VK_MEDIA_PREV_TRACK):
        return "Предыдущий трек."
    return "Spotify не запущен."


# --- системные вызовы ------------------------------------------------------
def _search_uri(query: str) -> str:
    return "spotify:search:" + urllib.parse.quote(query.strip(), safe="")


def _open_uri(uri: str) -> bool:
    """Открыть URI через обработчик схемы по умолчанию.

    ``os.startfile`` — штатный способ Windows: ShellExecute передаёт
    ``spotify:``-схему установленному клиенту. Вне Windows возвращает
    ``False``.
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        os.startfile(uri)  # type: ignore[attr-defined]  # есть только на Windows
    except OSError:
        return False
    return True


def _media_key(virtual_key: int) -> bool:
    """«Нажать» системную мультимедийную клавишу (аналог кнопки на клавиатуре).

    ``keybd_event`` с VK_кодами MEDIA_* доставляет событие всем приложениям,
    подписанным на глобальные мультимедийные сообщения, — Spotify в их
    числе. Вне Windows функция бессильна.
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        user32.keybd_event(virtual_key, 0, _KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(
            virtual_key, 0, _KEYEVENTF_EXTENDEDKEY | _KEYEVENTF_KEYUP, 0
        )
    except (AttributeError, OSError):
        return False
    return True


def _web_remote(method: str) -> bool:
    """Вызвать метод Web Remote API локального клиента Spotify.

    Десктопный клиент поднимает HTTP-сервер на ``127.0.0.1:8020–8022`` и
    принимает ``PUT /remote/control/<method>`` без авторизации. Если клиент
    не запущен, соединение отказывается мгновенно — перебираем порты и
    возвращаем ``False``.
    """
    for port in WEB_REMOTE_PORTS:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/remote/control/{method}",
            method="PUT",
            data=b"",
        )
        try:
            with urllib.request.urlopen(request, timeout=WEB_REMOTE_TIMEOUT_S) as response:
                if 200 <= response.status < 300:
                    return True
        except (urllib.error.HTTPError, urllib.error.URLError, OSError):
            continue
    return False
