# Спецификация модуля конфигурации CapriPet

## 1. Общие сведения и назначение
Модуль конфигурации предназначен для централизованного хранения, валидации, реактивного сохранения и безопасной загрузки пользовательских настроек приложения CapriPet.

Ключевые сущности для сохранения:
- Выбранный монитор (`designated_screen`)
- Выбранный микрофон (`designated_microphone`)
- Режим отображения, поза и масштаб (`appearance.pose`, `appearance.scale`, `appearance.skin`)
- Экранные глитчи и интенсивность (`effects.glitches_enabled`, `effects.glitch_intensity`)
- Голосовой ввод (`audio.voice_enabled`)
- Громкость звуковых эффектов и медиа (`audio.volume`, `audio.sfx_volume`, `audio.media_volume`)
- Позиция окон на экране (`window.position`, `window.terminal_position`, `window.overlay_position`)
- Начальная поза оверлея (`appearance.overlay_pose`) и скин (`appearance.skin`)
- Параметры поведения (`behavior.inactivity_timeout_ms`, `behavior.reminders_enabled`)
- Игровой режим (`game_mode.suppression_enabled`, списки `whitelist`/`blacklist`)
- Интеграция Discord RPC (`discord.enabled`, `discord.client_id`)

---

## 2. Место хранения и формат файла

### 2.1. Формат
- **JSON** (UTF-8, отступы `indent=2`, `ensure_ascii=False`).
- Имя файла: `config.json`.

### 2.2. Иерархия путей сохранения
1. **Основное централизованное хранилище (локальный каталог проекта):**
   `<project_root>/.capri/config.json`.
2. **Резервный системный каталог (фолбэк):**
   `%APPDATA%\capri\config.json`.
3. **Временная системная директория (фолбэк при недоступности записи):**
   `/tmp/capri_config.json` (или системный tempdir).

### 2.3. Обратная совместимость и миграция
- Если файл `config.json` отсутствует, но обнаружен старый `settings.json`, модуль автоматически считывает из него поля (`designated_screen`, `designated_microphone`) и конвертирует их в новую структуру `config.json`.

### 2.4. Безопасность и атомарность записи
- Запись производится во временный файл в том же каталоге (`config.json.tmp`) с последующим вызовом `os.replace(...)`. Это исключает повреждение или обнуление файла конфигурации при внезапном сбое питания или падении процесса.

---

## 3. Схема конфигурации (JSON Schema & Defaults)

### 3.1. Структура JSON по умолчанию

```json
{
  "version": 1,
  "screen": {
    "designated_screen": null
  },
  "audio": {
    "designated_microphone": null,
    "volume": 50,
    "sfx_volume": 0.5,
    "media_volume": 0.6,
    "voice_enabled": true,
    "speech_sound_enabled": true,
    "effects_sound_enabled": true
  },
  "appearance": {
    "skin": "default",
    "pose": "sit",
    "overlay_pose": "sit",
    "scale": 100
  },
  "effects": {
    "glitches_enabled": true,
    "glitch_intensity": "weak"
  },
  "window": {
    "position": null,
    "overlay_position": null,
    "terminal_position": null
  },
  "behavior": {
    "inactivity_timeout_ms": 5000,
    "reminders_enabled": true,
    "reminder_min_interval_ms": 600000,
    "reminder_max_interval_ms": 3600000,
    "file_shredder_enabled": true
  },
  "game_mode": {
    "suppression_enabled": true,
    "cooldown_seconds": 3.0,
    "whitelist": [],
    "blacklist": [
      "steam.exe",
      "steamwebhelper.exe",
      "epicgameslauncher.exe",
      "unrealcefsubprocess.exe",
      "unitycrashhandler64.exe",
      "riotclientux.exe",
      "galaxyclient.exe",
      "battlenet.exe"
    ]
  },
  "network": {
    "user_agent": null
  },
  "discord": {
    "enabled": true,
    "client_id": "1567968896277938266"
  }
}
```

### 3.2. Детальная спецификация полей

| Путь к ключу | Тип | Default | Допустимые значения / Описание |
|---|---|---|---|
| `version` | `int` | `1` | Версия схемы (для управления будущими миграциями) |
| `screen.designated_screen` | `str \| null` | `null` | Имя монитора (например, `"HDMI-1"`, `"eDP-1"`). `null` = системный экран |
| `audio.designated_microphone` | `str \| null` | `null` | Описание аудиоустройства ввода. `null` = системный микрофон по умолчанию |
| `audio.volume` | `int` | `50` | Общая системная громкость (25, 50, 75, 100) |
| `audio.sfx_volume` | `float` | `0.5` | Громкость звуков интерфейса и речи (0.0 .. 1.0) в `SpeechSFX` |
| `audio.media_volume` | `float` | `0.6` | Громкость медиа и видео (0.0 .. 1.0) |
| `audio.voice_enabled` | `bool` | `true` | Состояние голосового распознавания при старте (`VoiceInput`) |
| `audio.speech_sound_enabled` | `bool` | `true` | Воспроизведение звуков сообщений и облачков текста |
| `audio.effects_sound_enabled` | `bool` | `true` | Воспроизведение звуков эффектов и молний |
| `appearance.skin` | `str` | `"default"` | Имя скина/пака ресурсов |
| `appearance.pose` | `str` | `"sit"` | Текущая поза питомца: `"sit"`, `"stay"`, `"crouch"` |
| `appearance.overlay_pose` | `str` | `"sit"` | Поза оверлея по умолчанию: `"sit"`, `"stay"`, `"crouch"` |
| `appearance.scale` | `int` | `100` | Масштаб спрайта питомца в процентах (50, 75, 100, 125, 150) |
| `effects.glitches_enabled` | `bool` | `true` | Включены ли экранные глитч-эффекты (`GlitchManager`) |
| `effects.glitch_intensity` | `str` | `"weak"` | Интенсивность глитчей: `"weak"`, `"medium"`, `"strong"` |
| `window.position` | `{"x": int, "y": int} \| null` | `null` | Координаты положения окна на рабочем столе. `null` = центр экрана |
| `window.terminal_position` | `{"x": int, "y": int} \| null` | `null` | Координаты окна терминала на рабочем столе |
| `window.overlay_position` | `{"x": int, "y": int} \| null` | `null` | Координаты оверлея питомца на рабочем столе |
| `behavior.inactivity_timeout_ms`| `int` | `5000` | Время активности до скрытия питомца в миллисекундах (`5000`, `10000`, `15000`) |
| `behavior.reminders_enabled` | `bool` | `true` | Включены ли случайные напоминания Капри о себе |
| `behavior.reminder_min_interval_ms` | `int` | `600000` | Минимальный интервал периодических напоминаний (10 минут) |
| `behavior.reminder_max_interval_ms` | `int` | `3600000` | Максимальный интервал периодических напоминаний (60 минут) |
| `game_mode.suppression_enabled` | `bool` | `true` | Подавление всплывающего HUD и реплик при запуске полноэкранных игр |
| `game_mode.cooldown_seconds` | `float` | `3.0` | Задержка перед выходом из игрового режима при сворачивании игры |
| `game_mode.whitelist` | `list[str]` | `[]` | Белый список исполняемых файлов процессов |
| `game_mode.blacklist` | `list[str]` | `["steam.exe", ...]` | Черный список исполняемых файлов игр и лаунчеров |
| `network.user_agent` | `str \| null` | `null` | Пользовательский User-Agent (если null, генерируется автоматически) |
| `discord.enabled` | `bool` | `true` | Включена ли интеграция с Discord Rich Presence |
| `discord.client_id` | `str` | `"1567968896277938266"` | Client ID приложения Discord RPC |

---

## 4. Стратегия загрузки (Startup & Fallback)

При старте приложения загрузка выполняется до отображения интерфейса с соблюдением принципа отказоустойчивости (приложение никогда не должно падать из-за поврежденного конфига или отключенных устройств):

1. **Загрузка и парсинг файла:**
   - Если файл отсутствует — используются значения по умолчанию.
   - Если файл содержит синтаксическую ошибку (битый JSON) — регистрируется предупреждение через `logging.warning`, данные заменяются дефолтными.

2. **Монитор (`designated_screen`):**
   - Получение списка экранов `QGuiApplication.screens()`.
   - Если монитор с именем `designated_screen` найден в системе, окно привязывается к нему.
   - **Fallback:** Если монитор отключен или имя не найдено, используется `QGuiApplication.primaryScreen()` или первый доступный экран.

3. **Координаты окон (`position` / `overlay_position`):**
   - Если координаты заданы, проверяется, пересекается ли прямоугольник окна `QRect(x, y, w, h)` с областью `availableGeometry()` любого из подключенных мониторов.
   - **Fallback:** Если координаты находятся за пределами видимости (например, второй монитор отключили), окно автоматически центрируется на активном мониторе:
     `cx = geo.left() + (geo.width() - w) // 2`
     `cy = geo.top() + (geo.height() - h) // 2`

4. **Микрофон (`designated_microphone`):**
   - Поиск устройства в `QMediaDevices.audioInputs()` по `description()`.
   - Если устройство найдено — передается в `self._voice.set_device(dev)`.
   - **Fallback:** Если устройство не найдено или `designated_microphone is null`, используется `None` (дефолтный микрофон системы).

5. **Глитчи (`effects.glitches_enabled`):**
   - Вызывается `self._glitches.set_enabled(config["effects"]["glitches_enabled"])`.

6. **Голосовой ввод (`audio.voice_enabled`):**
   - Если параметр равен `false`, после инициализации вызывается остановка распознавания `self._voice.stop()`.

7. **Громкость звуков (`sfx_volume`, `media_volume`):**
   - Устанавливается `get_speech_sfx().set_volume(sfx_volume)`.
   - Устанавливается `self._media.audio.setVolume(media_volume)` и `sound_audio.setVolume(media_volume)`.

8. **Внешний вид и поза (`appearance.pose`, `appearance.scale`):**
   - Восстанавливается выбранная поза (`sit`, `stay`, `crouch`) и процент масштаба спрайта.

---

## 5. Стратегия сохранения (Save Strategy)

### 5.1. Реактивное сохранение при изменении в UI (On-Change)
При переключении любого элемента в контекстном меню или через шорткаты значение немедленно сохраняется в конфигурацию:
- **Выбор монитора:** обновление `screen.designated_screen`.
- **Выбор микрофона:** обновление `audio.designated_microphone`.
- **Тумблер глитчей:** обновление `effects.glitches_enabled` и `effects.glitch_intensity`.
- **Тумблер голоса:** обновление `audio.voice_enabled`.
- **Смена позы и масштаба:** обновление `appearance.pose`, `appearance.scale`.

### 5.2. Сохранение позиции окна
- В `mouseReleaseEvent` окна `CapriWindow` после перемещения пользователя обновляются координаты `position`.
- В `closeEvent` финальные координаты активного окна актуализируются в конфиге.

---

## 6. Требования к реализации для разработчика (`code`)

1. **Модуль `capri/core/settings.py`:**
   - Класс или модуль с методами:
     - `load_config() -> dict[str, Any]`
     - `save_config(data: dict[str, Any]) -> None`
     - `get_config_value(path: str, default: Any = None) -> Any` (доступ по точечной нотации, например `"audio.sfx_volume"`)
     - `set_config_value(path: str, value: Any) -> None`
   - Сохранение обратной совместимости с функциями `get_setting(key, default)` и `set_setting(key, value)`.
   - Атомарная запись через временный файл.

2. **Интеграция в `capri/ui/pet_window.py`:**
   - Расширение `_load_initial_settings()`: загрузка монитора, микрофона, глитчей, голоса, громкости, режима и геометрии.
   - Обновление обработчиков меню (`set_designated_screen`, `set_designated_microphone`, `_toggle_glitches`, `_toggle_voice`, `_toggle_capri_overlay`) для сохранения новых значений в конфиг.
   - Обработка сохранения позиции в `mouseReleaseEvent` и `closeEvent`.

3. **Тестирование:**
   - Модульные тесты на загрузку, дефолтные значения, сбои парсинга, проверку выхода за границы экранов (fallback), миграцию со старого формата и атомарную запись.
