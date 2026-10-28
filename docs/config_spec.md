# Спецификация модуля конфигурации CapriPet

## 1. Общие сведения и назначение
Модуль конфигурации предназначен для централизованного хранения, валидации, реактивного сохранения и безопасной загрузки пользовательских настроек приложения CapriPet.

Ключевые сущности для сохранения:
- Выбранный монитор (`designated_screen`)
- Выбранный микрофон (`designated_microphone`)
- Режим отображения (`appearance.mode`: окно терминала vs плавающий оверлей «Нормальный облик»)
- Экранные глитчи (`effects.glitches_enabled`)
- Голосовой ввод (`audio.voice_enabled`)
- Громкость звуковых эффектов и медиа (`sfx_volume`, `media_volume`)
- Позиция окон на экране (`terminal_position`, `overlay_position`)
- Начальная поза оверлея (`overlay_pose`) и скин (`skin`)
- Параметры поведения (`inactivity_timeout_ms`)

---

## 2. Место хранения и формат файла

### 2.1. Формат
- **JSON** (UTF-8, отступы `indent=2`, `ensure_ascii=False`).
- Имя файла: `config.json`.

### 2.2. Иерархия путей сохранения (XDG Base Directory)
1. **Основной системный каталог:**
   `$XDG_CONFIG_HOME/capri/config.json` (если переменная не задана: `~/.config/capri/config.json`).
2. **Локальный каталог проекта (фолбэк):**
   `<project_root>/.capri/config.json`
3. **Временная системная директория (фолбэк при недоступности записи):**
   `/tmp/capri_config.json`

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
    "sfx_volume": 0.5,
    "media_volume": 0.6,
    "voice_enabled": true,
    "speech_sound_enabled": true,
    "effects_sound_enabled": true
  },
  "appearance": {
    "mode": "terminal",
    "skin": "default",
    "overlay_pose": "sit",
    "scale": 100
  },
  "effects": {
    "glitches_enabled": true
  },
  "window": {
    "terminal_position": null,
    "overlay_position": null
  },
  "behavior": {
    "inactivity_timeout_ms": 5000
  }
}
```

### 3.2. Детальная спецификация полей

| Путь к ключу | Тип | Default | Допустимые значения / Описание |
|---|---|---|---|
| `version` | `int` | `1` | Версия схемы (для управления будущими миграциями) |
| `screen.designated_screen` | `str \| null` | `null` | Имя монитора (например, `"HDMI-1"`, `"eDP-1"`). `null` = системный экран |
| `audio.designated_microphone` | `str \| null` | `null` | Описание аудиоустройства ввода. `null` = системный микрофон по умолчанию |
| `audio.sfx_volume` | `float` | `0.5` | Громкость звуков интерфейса и речи (0.0 .. 1.0) в `SpeechSFX` |
| `audio.media_volume` | `float` | `0.6` | Громкость медиа и видео (0.0 .. 1.0) в `MediaController` |
| `audio.voice_enabled` | `bool` | `true` | Состояние голосового распознавания при старте (`VoiceInput`) |
| `audio.speech_sound_enabled` | `bool` | `true` | Воспроизведение звуков сообщений и облачков текста |
| `audio.effects_sound_enabled` | `bool` | `true` | Воспроизведение звуков эффектов и молний |
| `appearance.mode` | `str` | `"terminal"` | Режим отображения: `"terminal"` (окно) или `"overlay"` (спрайт питомца) |
| `appearance.skin` | `str` | `"default"` | Имя скина/пака ресурсов |
| `appearance.overlay_pose` | `str` | `"sit"` | Поза по умолчанию: `"sit"`, `"stay"`, `"crouch"` |
| `appearance.scale` | `int` | `100` | Масштаб спрайта питомца в процентах (50, 75, 100, 125, 150) |
| `effects.glitches_enabled` | `bool` | `true` | Включены ли экранные глитч-эффекты (`GlitchManager`) |
| `window.terminal_position` | `{"x": int, "y": int} \| null` | `null` | Координаты окна терминала на рабочем столе. `null` = центр экрана |
| `window.overlay_position` | `{"x": int, "y": int} \| null` | `null` | Координаты оверлея питомца на рабочем столе. `null` = центр экрана |
| `behavior.inactivity_timeout_ms`| `int` | `5000` | Время бездействия до анимации/скрытия в миллисекундах |

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

3. **Координаты окон (`terminal_position` / `overlay_position`):**
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

8. **Режим отображения (`appearance.mode`):**
   - Если сохранен режим `"overlay"`, при старте инициируется переключение в оверлей (`_toggle_capri_overlay()`).

---

## 5. Стратегия сохранения (Save Strategy)

### 5.1. Реактивное сохранение при изменении в UI (On-Change)
При переключении любого элемента в контекстном меню или через шорткаты значение немедленно сохраняется в конфигурацию:
- **Выбор монитора:** обновление `screen.designated_screen`.
- **Выбор микрофона:** обновление `audio.designated_microphone`.
- **Тумблер глитчей:** обновление `effects.glitches_enabled`.
- **Тумблер голоса:** обновление `audio.voice_enabled`.
- **Смена режима (Окно / Оверлей):** обновление `appearance.mode`.

### 5.2. Сохранение позиции окна
- В `mouseReleaseEvent` обоих окон (`CapriWindow` и `CapriOverlayWindow`) после перемещения пользователя обновляются координаты `terminal_position` или `overlay_position`.
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
