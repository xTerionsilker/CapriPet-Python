from __future__ import annotations

from dataclasses import dataclass

from .commands import CommandRegistry, Handler


@dataclass(frozen=True)
class Handlers:

    toggle_glitches: Handler
    toggle_voice: Handler
    wild_glitch: Handler
    ask_ollama: Handler
    search_google: Handler
    search_youtube: Handler
    spotify_play: Handler
    spotify_pause: Handler
    spotify_resume: Handler
    spotify_next: Handler
    spotify_previous: Handler
    lock_screen: Handler
    power_off: Handler
    suspend: Handler
    reboot: Handler
    toggle_overlay: Handler


def register_commands(registry: CommandRegistry, handlers: Handlers) -> None:
    registry.register(
        "комплимент",
        "устроить дикие глитчи на 5 секунд.",
        handlers.wild_glitch,
        aliases=(
            "ты красивая",
            "капри ты красивая",
            "ты самая лучшая",
            "ты прекрасна",
            "комплимент капри",
        ),
        keywords=("комплимент", "красив", "лучш", "прекрасн", "восторг"),
    )
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
        requires_confirmation=True,
    )
    registry.register(
        "я спать",
        "выключить компьютер.",
        handlers.power_off,
        aliases=(
            "выключи пк",
            "выключить пк",
            "выключи компьютер",
            "выключить компьютер",
            "выруби пк",
            "выруби компьютер",
            "выключись",
            "спокойной ночи",
            "shutdown",
            "poweroff",
            "выключение пк",
            "выключить",
        ),
        keywords=("спат", "спят", "выключ", "shutdown", "poweroff", "питан"),
        requires_confirmation=True,
    )
    registry.register(
        "я гулять",
        "перевести компьютер в спящий режим.",
        handlers.suspend,
        aliases=(
            "спящий режим",
            "перевести в спящий режим",
            "переведи в спящий режим",
            "режим сна",
            "усни",
            "уснуть",
            "сон",
            "замри",
            "приостанови компьютер",
            "sleep",
        ),
        keywords=("спящ", "сон", "усн", "suspend", "замр", "гуля"),
        requires_confirmation=True,
    )
    registry.register(
        "я заебался",
        "перезагрузить компьютер.",
        handlers.reboot,
        aliases=(
            "перезагрузи",
            "перезагрузить",
            "перезагрузи пк",
            "выключить и включить",
            "перезагрузи компьютер",
            "перезагрузка",
            "рестарт",
            "restart",
            "reboot",
        ),
        keywords=("перезагруз", "рестарт", "restart", "reboot", "заебал"),
        requires_confirmation=True,
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

    registry.register(
        "Нормальный облик",
        "переключить между окном Капри и оверлеем-картинкой поверх окон.",
        handlers.toggle_overlay,
        aliases=(
            "нормальный облик",
            "нормальный вид",
            "капри оверлей",
            "оверлей капри",
            "режим оверлея",
            "режим капри",
            "покажи капри",
            "капри на экран",
            "капри поверх окон",
            "капри картинка",
            "облик капри",
            "переключить облик",
            "переключить оверлей",
            "капри pet",
            "capri overlay",
            "overlay mode",
            "normal form",
            "покажи облик",
            "режим картинки",
        ),
        keywords=(
            "облик",
            "оверлей",
            "overlay",
            "картинк",
            "поверх",
            "режим",
            "нормальн",
        ),
    )
