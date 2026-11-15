"""Централизованный менеджер текстовых реплик и стилей общения CapriPet."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, Field

from .settings import get_config_value, set_config_value

logger = logging.getLogger(__name__)

DEFAULT_STYLE_ID: Final[str] = "arasaka_engram"


class DialogueMeta(BaseModel):
    """Метаданные пресета стиля диалогов."""

    id: str
    name: str
    description: str = ""


class InactivityDialogue(BaseModel):
    """Реплики напоминаний и неактивности."""

    reminders: list[str] = Field(default_factory=list)


class PranksDialogue(BaseModel):
    """Реплики уворотов и сбоев энграммы."""

    dodge: list[str] = Field(default_factory=list)
    relic_fault: str = ">> [RELIC_FAULT: 0xDEADBEEF] SECTOR_CORRUPT"
    relic_recover: str = "Кхм... опять шина памяти барахлит. Не обращай внимания, хост."


class ShredderDialogue(BaseModel):
    """Реплики поглощения и уничтожения данных Blackwall."""

    blocked: str = "Эй, руки убрал! Я сижу в этой системе — сломаешь ядро, и где я жить буду?"
    empty: str = "Пустота? Ты мне битый фантом подсунул, хост? Не смешно, давай нормальные данные!"
    tiny: str = "Ха! И это всё? Серьёзно, жалкие {bytes} байт? Давай пожирнее!"
    huge: str = "О-о-о, вот это нажористо! Целых {gb:.1f} ГБ в пыль и труху!"
    binary: str = "Опа, сочный бинарник ({ext})! Размазала по битам за наносекунду."
    junk: str = "Фу, корпоратский мусор ({ext})! С тебя должок!"
    script: str = "Смотри, как красиво плавятся эти скрипты ({ext})!"
    archive: str = "Обожаю архивы — как хлопушка с конфетти! Пыщ — и '{name}' разлетелся в вакуум!"
    folder: str = "Папка '{name}' и все её {count} файлов ушли в небытие."
    default: str = "Ням! '{name}' ({mb:.1f} МБ) аннигилирован. Даже цифрового пепла не осталось!"

class DialoguePreset(BaseModel):
    """Корневая модель пресета диалогов CapriPet."""

    meta: DialogueMeta
    inactivity: InactivityDialogue = Field(default_factory=InactivityDialogue)
    process_reactions: dict[str, list[str]] = Field(default_factory=dict)
    pranks: PranksDialogue = Field(default_factory=PranksDialogue)
    shredder: ShredderDialogue = Field(default_factory=ShredderDialogue)
    commands: dict[str, str] = Field(default_factory=dict)


_FALLBACK_PRESET_DATA: dict[str, Any] = {
    "meta": {
        "id": DEFAULT_STYLE_ID,
        "name": "Arasaka Engram",
        "description": "Каноничная нестабильная цифровая энграмма",
    },
    "inactivity": {
        "reminders": [
            "Эй, хост, ты там уснул на клавиатуре? У меня уже электроны затекают от скуки!",
            "Протокол самоликвидации через 3... 2... Ладно, шучу! Просто проверяю твой пульс, хе-хе.",
            "Капри умирает от цифровой тоски! Подкинь задачку или хотя бы музыку вруби!",
            "Эй, мясной! Твой мозговой имплант не перегрелся? Ты подозрительно долго молчишь.",
            "Внимание, синапсы стынут! Верни меня в фокус, пока я не начала ломать реестры от скуки!",
        ]
    },
    "process_reactions": {
        "dev": ["Опять открыл компилятор, мясной? Смотри не перегрузи мой стек своими багами!"],
        "web": ["Опять сёрфишь сеть? Твой браузер пожирает память жаднее, чем Черный заслон!"],
        "media": ["Врубил музыку? Ладно, этот бит хотя бы заглушает шум твоих медленных синапсов."],
        "corpo": ["Серьёзно, офисный софт? Этот корпо-мусор убивает мои нейроны быстрее Душегуба!"],
        "heavy": ["Ого, тяжелая артиллерия! Чувствую, как кремний на твоем процессоре начинает плавиться."],
    },
    "pranks": {
        "dodge": [
            "Слишком медленные синапсы, мясной. Попробуй ещё раз!",
            "Думал поймал? Я цифровой конструкт, а не твой коврик для мыши.",
            "Мимо! Мой отклик — три наносекунды, твой — полвека.",
            "Руки от биочипа убрал! Контакт не для твоих пальцев.",
            "Ха! Пинг проверь, хост. Я уже в другом секторе экрана.",
        ],
        "relic_fault": ">> [RELIC_FAULT: 0xDEADBEEF] SECTOR_CORRUPT // SOULKILLER_V4_INTEGRITY_FAIL",
        "relic_recover": "Кхм... опять шина памяти барахлит. Не обращай внимания, хост.",
    },
    "shredder": {
        "blocked": "Эй, руки убрал! Ты куда свои клешни тянешь?!",
        "empty": "Пустота? Ты мне битый фантом подсунул, хост?",
        "tiny": "Ха! И это всё? Серьёзно, жалкие {bytes} байт?",
        "huge": "О-о-о, вот это нажористо! Целых {gb:.1f} ГБ в пыль и труху!",
        "binary": "Опа, сочный бинарник ({ext})! Размазала по битам за наносекунду.",
        "junk": "Фу, корпоратский мусор ({ext})!",
        "script": "Смотри, как красиво плавятся эти скрипты ({ext})!",
        "archive": "Обожаю архивы — как хлопушка с конфетти!",
        "folder": "Папка '{name}' и все её {count} файлов ушли в небытие.",
        "default": "Ням! '{name}' ({mb:.1f} МБ) аннигилирован.",
    },
    "commands": {
        "app_not_found": "Отказ! В твоих каталогах нет ничего похожего. Ты точно не опечатался?",
        "proc_not_found": "Ни одного такого процесса в памяти нет. Кого глушить-то собрался, призраков?",
    },
}

class DialogueManager:
    """Менеджер стилей реплик и динамический резолвер фраз персонажа."""

    def __init__(self, dialogues_dir: Path | None = None) -> None:
        self._dir = dialogues_dir or (
            Path(__file__).resolve().parents[2] / "assets" / "dialogues"
        )
        self._presets: dict[str, DialoguePreset] = {}
        self._active_style: str = DEFAULT_STYLE_ID
        self.reload()

    def reload(self) -> None:
        """Перезагружает все файлы пресетов из директории ассетов."""
        self._presets.clear()
        if self._dir.is_dir():
            for file_path in sorted(self._dir.glob("*.json")):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)
                    preset = DialoguePreset.model_validate(data)
                    self._presets[preset.meta.id] = preset
                except Exception as e:
                    logger.warning("Ошибка загрузки пресета %s: %s", file_path, e)

        if DEFAULT_STYLE_ID not in self._presets:
            self._presets[DEFAULT_STYLE_ID] = DialoguePreset.model_validate(
                _FALLBACK_PRESET_DATA
            )

        saved_style = get_config_value("behavior.dialogue_style", DEFAULT_STYLE_ID)
        self.set_style(saved_style, persist=False)

    @property
    def current_style(self) -> str:
        return self._active_style

    @property
    def active_preset(self) -> DialoguePreset:
        return self._presets.get(
            self._active_style, self._presets[DEFAULT_STYLE_ID]
        )

    def list_styles(self) -> list[DialogueMeta]:
        """Возвращает список метаданных всех доступных стилей."""
        return [p.meta for p in self._presets.values()]

    def set_style(self, style_id: str, *, persist: bool = True) -> bool:
        """Устанавливает активный стиль диалогов."""
        if style_id in self._presets:
            self._active_style = style_id
        else:
            self._active_style = DEFAULT_STYLE_ID
        if persist:
            set_config_value("behavior.dialogue_style", self._active_style)
        return self._active_style == style_id

    def get_reminder_phrases(self) -> tuple[str, ...]:
        """Возвращает список фраз напоминания о присутствии."""
        reminders = self.active_preset.inactivity.reminders
        if not reminders:
            reminders = self._presets[DEFAULT_STYLE_ID].inactivity.reminders
        return tuple(reminders)

    def get_process_reactions(self, category: str) -> tuple[str, ...]:
        """Возвращает фразы реакции на указанную категорию процессов."""
        cat_map = self.active_preset.process_reactions
        phrases = cat_map.get(category.lower())
        if not phrases:
            default_map = self._presets[DEFAULT_STYLE_ID].process_reactions
            phrases = default_map.get(category.lower(), [])
        return tuple(phrases)

    def get_dodge_phrases(self) -> tuple[str, ...]:
        """Возвращает фразы уворота от курсора мыши."""
        dodge = self.active_preset.pranks.dodge
        if not dodge:
            dodge = self._presets[DEFAULT_STYLE_ID].pranks.dodge
        return tuple(dodge)

    def get_prank_phrase(self, key: str) -> str:
        """Возвращает строку сбоя энграммы (relic_fault / relic_recover)."""
        val = getattr(self.active_preset.pranks, key, None)
        if not val:
            val = getattr(self._presets[DEFAULT_STYLE_ID].pranks, key, "")
        return str(val)

    def get_shredder_phrase(self, key: str, **kwargs: Any) -> str:
        """Возвращает реплику уничтожения данных с подстановкой параметров."""
        raw = getattr(self.active_preset.shredder, key, None)
        if not raw:
            raw = getattr(self._presets[DEFAULT_STYLE_ID].shredder, key, "")
        raw_str = str(raw or "")
        try:
            return raw_str.format(**kwargs) if kwargs else raw_str
        except Exception:
            return raw_str

    def generate_shred_dialogue(
        self, metrics: Any = None, blocked: bool = False
    ) -> str:
        """Генерирует реплику энграммы по метрикам уничтоженных файлов."""
        if blocked or metrics is None:
            return self.get_shredder_phrase("blocked")

        total_files = getattr(metrics, "total_files", 0)
        total_dirs = getattr(metrics, "total_dirs", 0)
        total_bytes = getattr(metrics, "total_bytes", 0)
        sample_name = getattr(metrics, "sample_name", "")
        ext = getattr(metrics, "dominant_extension", "")

        if total_files == 0 and total_dirs == 0:
            return self.get_shredder_phrase("empty")

        size_mb = total_bytes / (1024 * 1024)
        if total_bytes < 1024:
            return self.get_shredder_phrase("tiny", bytes=total_bytes, name=sample_name)
        if size_mb > 1024:
            return self.get_shredder_phrase("huge", gb=size_mb / 1024)

        if ext in (".exe", ".dll", ".bin"):
            return self.get_shredder_phrase("binary", ext=ext)
        if ext in (".log", ".tmp", ".bak", ".dump"):
            return self.get_shredder_phrase("junk", ext=ext)
        if ext in (".py", ".js", ".cpp", ".rs", ".java", ".html", ".css", ".ts"):
            return self.get_shredder_phrase("script", ext=ext)
        if ext in (".zip", ".rar", ".7z", ".tar", ".gz"):
            return self.get_shredder_phrase("archive", name=sample_name)

        if total_dirs > 0:
            return self.get_shredder_phrase("folder", name=sample_name, count=total_files)

        return self.get_shredder_phrase("default", name=sample_name, mb=size_mb)

    def get_command_phrase(self, key: str, default: str = "", **kwargs: Any) -> str:
        """Возвращает реплику команды из раздела commands с подстановкой параметров."""
        raw = self.active_preset.commands.get(key)
        if not raw:
            raw = self._presets[DEFAULT_STYLE_ID].commands.get(key, default)
        raw_str = str(raw or "")
        try:
            return raw_str.format(**kwargs) if kwargs else raw_str
        except Exception:
            return raw_str




_dialogue_manager_instance: DialogueManager | None = None


def get_dialogue_manager() -> DialogueManager:
    """Возвращает глобальный синглтон DialogueManager."""
    global _dialogue_manager_instance
    if _dialogue_manager_instance is None:
        _dialogue_manager_instance = DialogueManager()
    return _dialogue_manager_instance
