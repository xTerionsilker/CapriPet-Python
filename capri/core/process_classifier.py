"""Семантический классификатор процессов и матрица контекстных реплик Капри."""

from __future__ import annotations

import random
from typing import Final

# Категории процессов по умолчанию
DEFAULT_PROCESS_CATEGORIES: Final[dict[str, tuple[str, ...]]] = {
    "dev": (
        "code.exe",
        "pycharm64.exe",
        "pycharm.exe",
        "devenv.exe",
        "windowsterminal.exe",
        "wt.exe",
        "powershell.exe",
        "cmd.exe",
        "sublime_text.exe",
        "idea64.exe",
        "clion64.exe",
        "rider64.exe",
        "webstorm64.exe",
        "git-bash.exe",
    ),
    "web": (
        "chrome.exe",
        "firefox.exe",
        "msedge.exe",
        "opera.exe",
        "brave.exe",
        "vivaldi.exe",
        "yandex.exe",
    ),
    "media": (
        "spotify.exe",
        "vlc.exe",
        "aimp.exe",
        "foobar2000.exe",
        "musicbee.exe",
        "itunes.exe",
        "wmplayer.exe",
    ),
    "corpo": (
        "excel.exe",
        "winword.exe",
        "powerpnt.exe",
        "slack.exe",
        "teams.exe",
        "telegram.exe",
        "outlook.exe",
        "onenote.exe",
        "notion.exe",
    ),
    "heavy": (
        "blender.exe",
        "afterfx.exe",
        "premiere.exe",
        "unrealeditor.exe",
        "unity.exe",
        "resolve.exe",
        "maya.exe",
        "3dsmax.exe",
    ),
}

# Реплики энграммы Каприкорн (Soulkiller / Arasaka lore)
DEFAULT_CATEGORY_PHRASES: Final[dict[str, tuple[str, ...]]] = {
    "dev": (
        "Опять открыл компилятор, мясной? Смотри не перегрузи мой стек своими багами!",
        "Решил покодить? Если уронишь память хоста, я лично взломаю твой терминал.",
        "Так-так, кодим под моим надзором. Мой ледоруб быстрее любого твоего алгоритма!",
        "Вижу терминал в памяти. Только не вздумай компилировать мусор в моем субстрате!",
    ),
    "web": (
        "Опять сёрфишь сеть? Твой браузер пожирает память жаднее, чем Черный заслон!",
        "Мясной, ты снова сливаешь гигабайты впустую. Закрой пару сотен вкладок, не позорься.",
        "Бесконечный сёрфинг... Я сканирую трафик, и тут сплошная прокрастинация!",
        "Браузер на переднем плане. Если оперативка закипит — винить будешь себя, хост.",
    ),
    "media": (
        "Врубил музыку? Ладно, этот бит хотя бы заглушает шум твоих медленных синапсов.",
        "Медиапоток пошёл по шине. Надеюсь, у тебя хороший вкус, иначе я сама переключу трек!",
        "Звуковая дорожка активирована. Не отвлекайся слишком сильно, у нас ещё дела в системе.",
    ),
    "corpo": (
        "Серьёзно, офисный софт? Этот корпо-мусор убивает мои нейроны быстрее Душегуба!",
        "Таблички и документы? Мясной, ты тратишь мощь биочипа на бумажную волокиту Арасаки?",
        "Скука смертная! Как ты вообще выдерживаешь эту корпоративную рутину?",
    ),
    "heavy": (
        "Ого, тяжелая артиллерия! Чувствую, как кремний на твоем процессоре начинает плавиться.",
        "Такой рендер даже мои контуры разогрел. Держи огнетушитель наготове, партнёр!",
        "Врубил тяжёлый софт? Не сожги материнку, мне ещё жить в этом нейролинке!",
    ),
}


class ProcessClassifier:
    """Классификатор исполняемых файлов процессов и генератор реплик."""

    def __init__(self, custom_rules: dict[str, str] | None = None) -> None:
        self._custom_rules: dict[str, str] = {
            k.lower(): v.lower() for k, v in (custom_rules or {}).items()
        }
        self._reverse_map: dict[str, str] = {}
        self._build_reverse_map()

    def _build_reverse_map(self) -> None:
        """Строит плоский кэш поиска 'proc_name -> category'."""
        self._reverse_map.clear()
        for category, exes in DEFAULT_PROCESS_CATEGORIES.items():
            for exe in exes:
                self._reverse_map[exe.lower()] = category
        # Пользовательские правила имеют приоритет
        for exe, category in self._custom_rules.items():
            self._reverse_map[exe.lower()] = category

    def update_custom_rules(self, custom_rules: dict[str, str]) -> None:
        """Обновляет пользовательские правила сопоставления процессов."""
        self._custom_rules = {k.lower(): v.lower() for k, v in custom_rules.items()}
        self._build_reverse_map()

    def classify(self, process_name: str) -> str | None:
        """Возвращает категорию процесса или None, если процесс неизвестен."""
        if not process_name:
            return None
        clean_name = process_name.strip().lower()
        return self._reverse_map.get(clean_name)

    def get_reaction_phrase(
        self,
        category: str,
        custom_phrases: dict[str, list[str]] | None = None,
    ) -> str:
        """Возвращает случайную саркастичную реплику для указанной категории."""
        pool: list[str] = []
        if custom_phrases and category in custom_phrases:
            pool.extend(custom_phrases[category])
        if category in DEFAULT_CATEGORY_PHRASES:
            pool.extend(DEFAULT_CATEGORY_PHRASES[category])

        if not pool:
            return f"Зафиксирован запуск {category}. Мои датчики не упускают ни единого процесса!"

        return random.choice(pool)
