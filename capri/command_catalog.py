"""Каталог встроенных команд Capri.

Здесь описано, какие команды есть, как их распознавать (псевдонимы и
смысловые подсказки ``keywords``) и каким обработчикам они соответствуют.
Сами обработчики — методы окна из ``capri.pet_window``: окно собирает их в
:class:`Handlers` и передаёт в :func:`register_commands`, поэтому каталог
не знает ничего о виджетах.

Чтобы добавить свою команду, трогать этот модуль не обязательно —
зарегистрируйте её через ``registry.register(...)`` в ``CapriWindow.__init__``
(см. README).

Пример::

    from capri.command_catalog import Handlers, register_commands
    from capri.commands import CommandRegistry

    handlers = Handlers(toggle_glitches=lambda: "Готово.", ...)
    registry = CommandRegistry()
    register_commands(registry, handlers)
"""

from __future__ import annotations

from dataclasses import dataclass

from .commands import CommandRegistry, Handler


@dataclass(frozen=True)
class Handlers:
    """Обработчики встроенных команд, предоставляемые главным окном."""

    toggle_glitches: Handler
    toggle_noise: Handler
    toggle_voice: Handler
    ask_ollama: Handler
    search_google: Handler
    search_youtube: Handler
    spotify_play: Handler
    spotify_pause: Handler
    spotify_resume: Handler
    spotify_next: Handler
    spotify_previous: Handler
    lock_screen: Handler


def register_commands(registry: CommandRegistry, handlers: Handlers) -> None:
    """Зарегистрировать все встроенные команды в ``registry``."""
    registry.register(
        "глитч",
        "включить или выключить экранные глитчи.",
        handlers.toggle_glitches,
        aliases=(
            "переключить глитч",
            "включить глитч",
            "выключить глитч",
            "глитчи",
            "глюки",
            "переключить глюки",
            "включить глюки",
            "выключить глюки",
            "эффекты",
            "переключить эффекты",
        ),
        keywords=(
            "глитч",
            "глюк",
            "эффект",
            "цвет",
            "радуг",
            "визуал",
            "помех",
            "искажен",
        ),
    )
    registry.register(
        "шум",
        "включить или выключить фоновый шум.",
        handlers.toggle_noise,
        aliases=(
            "переключить шум",
            "включить шум",
            "выключить шум",
            "шипение",
            "переключить шипение",
            "включить шипение",
            "выключить шипение",
            "статика",
            "звук",
            "включить звук",
            "выключить звук",
        ),
        keywords=("шум", "шип", "статик", "треск", "звук"),
    )
    registry.register(
        "голос",
        "начать или остановить голосовой ввод.",
        handlers.toggle_voice,
        aliases=(
            "микрофон",
            "слушать",
            "говорить",
            "голосовой ввод",
            "запись",
            "включить голос",
            "выключить голос",
            "включить микрофон",
            "выключить микрофон",
        ),
        keywords=("голос", "микрофон", "слуша", "говори", "запис"),
    )
    registry.register(
        "гугл",
        "найти запрос в Google.",
        handlers.search_google,
        aliases=(
            "загугли",
            "погугли",
            "гуглить",
            "искать в гугле",
            "найди в гугле",
            "поищи в гугле",
            "поискать в гугле",
            "поиск в гугле",
            "google",
            "искать в google",
            "найди в google",
            "поищи в google",
            "поиск в google",
            "найди в интернете",
            "поищи в интернете",
        ),
        takes_argument=True,
        keywords=(
            "гугл",
            "google",
            "поиск",
            "интернет",
            "найди",
            "загугл",
            "погугл",
        ),
    )
    registry.register(
        "ютуб",
        "найти запрос на YouTube.",
        handlers.search_youtube,
        aliases=(
            "ютьюб",
            "youtube",
            "искать на ютубе",
            "найди на ютубе",
            "найди в ютубе",
            "поищи на ютубе",
            "поищи в ютубе",
            "поискать на ютубе",
            "поиск на ютубе",
            "поиск в ютубе",
            "искать на youtube",
            "найди на youtube",
            "поищи на youtube",
            "поиск на youtube",
        ),
        takes_argument=True,
        keywords=("ютуб", "youtube", "видео", "ролик", "ютюб"),
    )
    registry.register(
        "спотифай",
        "найти и включить музыку в Spotify.",
        handlers.spotify_play,
        aliases=(
            "spotify",
            "спотик",
            "включи музыку",
            "поставь музыку",
            "включи спотифай",
            "включи в спотифае",
            "найди музыку",
            "найди песню",
            "включи песню",
            "поставь песню",
        ),
        takes_argument=True,
        keywords=(
            "музык",
            "песн",
            "трек",
            "спотиф",
            "spotify",
            "плейлист",
            "альбом",
            "исполнител",
            "мелоди",
        ),
    )
    registry.register(
        "пауза",
        "поставить музыку в Spotify на паузу.",
        handlers.spotify_pause,
        aliases=(
            "поставь на паузу",
            "паузу",
            "приостанови музыку",
            "приостанови",
        ),
        keywords=("пауз", "останов", "стоп", "тихо", "приглуш"),
    )
    registry.register(
        "продолжить",
        "продолжить воспроизведение в Spotify.",
        handlers.spotify_resume,
        aliases=(
            "плей",
            "играй",
            "продолжи музыку",
            "возобнови",
            "возобнови музыку",
        ),
        keywords=("продолж", "играй", "возобнов", "плей", "громче"),
    )
    registry.register(
        "следующий трек",
        "включить следующий трек в Spotify.",
        handlers.spotify_next,
        aliases=(
            "следующий",
            "след",
            "next",
            "переключи трек",
            "следующая песня",
        ),
        keywords=("следующ", "дальше", "переключ", "next"),
    )
    registry.register(
        "предыдущий трек",
        "вернуться к предыдущему треку в Spotify.",
        handlers.spotify_previous,
        aliases=(
            "предыдущий",
            "prev",
            "previous",
            "предыдущая песня",
        ),
        keywords=("предыдущ", "назад", "prev", "верни"),
    )
    registry.register(
        "блокировка",
        "заблокировать экран (аналог Super+L).",
        handlers.lock_screen,
        aliases=(
            "заблокировать",
            "заблокируй",
            "блокировать",
            "заблокировать экран",
            "заблокируй экран",
            "экран блокировки",
            "блокировка экрана",
            "лок",
            "lock",
            "lock screen",
            "super+l",
            "я отойду",
            "отойду",
        ),
        keywords=("блокир", "заблок", "экран", "лок", "lock"),
    )
    registry.register(
        "слушай",
        "спросить локальную модель Ollama.",
        handlers.ask_ollama,
        aliases=(
            "спроси модель",
            "спроси локально",
            "локальная модель",
            "ollama",
            "оллама",
            "qwen",
        ),
        takes_argument=True,
        keywords=(
            "слушай",
            "ollama",
            "оллам",
            "qwen",
            "модел",
            "спроси",
            "спросить",
        ),
    )
