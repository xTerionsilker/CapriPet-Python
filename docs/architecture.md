# Архитектура CapriPet

Документ описывает программную архитектуру кибер-питомца CapriPet: взаимодействие подсистем, конвейер обработки речи, выполнение команд и отображение визуальных компонентов на базе PySide6 (Qt).

---

## 1. Общая архитектурная схема (C4 / Container & Component Level)

```mermaid
flowchart TB
    %% Входные сигналы
    subgraph Inputs["1. Источники ввода"]
        direction TB
        Mic["Микрофон (Аудиопоток)"]
        Hotkeys["Горячие клавиши (Ctrl+Space, Ctrl+Q)"]
        Mouse["События мыши / Трей / DWM"]
    end

    %% Аудио подсистема
    subgraph AudioSubsystem["2. Аудио и распознавание (capri.audio)"]
        direction TB
        Voice["voice.py<br/>(Захват звука, Silero VAD)"]
        ASR["recognizer.py<br/>(Vosk ASR)"]
        Voice -->|Фреймы речи| ASR
    end

    %% Ядро обработки
    subgraph CoreSubsystem["3. Конвейер ядра (capri.core)"]
        direction TB
        WakeWord["wake_word.py<br/>(Детектор активации «Капри»)"]
        InputFlow["input_flow.py<br/>(Конвейер сессий и подтверждений)"]
        Morphology["morphology.py<br/>(Стемминг, нормализация числительных)"]
        Classifier["process_classifier.py<br/>(Классификатор ПО и реплики)"]
        Settings["settings.py<br/>(Pydantic v2 .capri/config.json)"]

        WakeWord --> InputFlow
        Morphology -.-> InputFlow
        Classifier -.-> Settings
    end

    %% Контроллеры и оркестрация
    subgraph Controllers["4. Контроллеры и управление (capri.controllers)"]
        direction TB
        Orchestrator["orchestrator.py<br/>(Центральный оркестратор)"]
        Inactivity["inactivity_manager.py<br/>(Таймер неактивности + PresenceReminder)"]
        Watcher["process_watcher.py<br/>(Гибридный ProcessWatcher)"]
        ActionBridge["action_bridge.py<br/>(Асинхронный мост потоков)"]
    end

    %% Команды и интеграции
    subgraph CommandsSubsystem["5. Модульная система команд и интеграции"]
        direction TB
        Registry["commands/registry.py<br/>(Реестр и нечёткий поиск)"]
        Handlers["commands/handlers.py<br/>(Обработчики действий)"]
        Integrations["integrations/<br/>(Spotify, Discord RPC, AppLauncher, SystemControl, SystemVolume, GameMode, Cleaner, DataShredder)"]

        Registry --> Handlers
        Handlers --> Integrations
    end

    %% UI и Визуальные эффекты
    subgraph VisualPresentation["6. Графический интерфейс и эффекты (capri.ui / capri.effects)"]
        direction TB
        PetWindow["ui/pet_window.py & pet_window_actions.py<br/>(Главное окно питомца, View и ActionDelegate)"]
        PetRenderer["ui/pet_renderer.py<br/>(Рендерер спрайтов, глитч-ауры Blackwall и сканлайнов)"]
        ContextMenu["ui/context_menu.py<br/>(Кибер-меню и настройки)"]
        ConsoleHUD["ui/console_hud.py<br/>(CyberConsoleHud прямой ввод команд)"]
        VoiceCoord["ui/voice_coordinator.py<br/>(Координатор ASR & HUD)"]
        VoiceHUD["ui/voice_hud.py<br/>(Cyberpunk Voice HUD над taskbar)"]
        VolumeHUD["ui/volume_hud.py<br/>(CyberVolumeHud экранный OSD)"]
        SpeechHUD["ui/speech.py & speech_sfx.py<br/>(CyberHudBubble и синтез SFX)"]
        GameOverlay["ui/game_overlay.py<br/>(SilentPresenceGlyph оверлей)"]
        Effects["effects/effects_coordinator.py<br/>(CRT-глитчи, молнии, переходы)"]

        PetWindow --> PetRenderer
        PetWindow --> ContextMenu
        PetWindow --> ConsoleHUD
        PetWindow --> VolumeHUD
        VoiceCoord --> VoiceHUD
    end

    %% Связи между уровнями
    Mic --> Voice
    Hotkeys --> Orchestrator
    Mouse --> PetWindow

    ASR -->|Поток распознанного текста| WakeWord
    InputFlow -->|Командная фраза / подтверждение| Orchestrator

    Orchestrator <--> Registry
    Orchestrator --> ActionBridge
    ActionBridge --> Handlers
    Inactivity --> Orchestrator
    Watcher -->|Контекст активного/тяжелого ПО| Orchestrator

    Orchestrator -->|Состояние позы, речь, анимация| PetWindow
    Orchestrator -->|Координация статуса и текста ASR| VoiceCoord
    Orchestrator -->|Текст реплики| SpeechHUD
    Orchestrator -->|Запуск процедурных эффектов| Effects
```

---

## 2. Диаграмма последовательности голосовой команды (Sequence)

Ниже показан путь прохождения голосовой команды от микрофона до исполнения и обратной связи через HUD.

```mermaid
sequenceDiagram
    autonumber
    actor User as Пользователь
    participant Voice as voice.py (VAD)
    participant ASR as recognizer.py (Vosk)
    participant Core as wake_word / input_flow
    participant Orch as orchestrator.py
    participant Cmd as commands/registry & handlers
    participant Integ as integrations
    participant SFX as SpeechSFX
    participant UI as UI & Effects (HUD)

    User->>Voice: «Капри, запусти блокнот»
    Voice->>ASR: Аудио-чанкер (активность речи)
    ASR->>Core: Распознанная строка («капри запусти блокнот»)
    Core->>Core: Детекция триггера «капри» + нормализация
    Core->>Orch: Команда: «запусти блокнот»
    Orch->>SFX: play_voice_success() (кибер-аккорд)
    Orch->>UI: Активация Voice HUD (распознано)
    Orch->>Cmd: Поиск команды в реестре
    Cmd->>Integ: app_launcher.launch("блокнот")
    Integ-->>Cmd: Успешно / найдено 1 совпадение
    Cmd-->>Orch: CommandResult (текст ответа, эмоция)
    Orch->>UI: Показ диалогового облачка (speech.py) + звук (speech_sfx.py)
    Orch->>UI: Смена эмоции/спрайта питомца
```

---

## 3. Описание ключевых подсистем

1. **`capri.audio`**: Непрерывный низкоуровневый захват с аудиокарты, отсечение тишины моделью Silero VAD и передача активных отрезков в локальную модель ASR (Vosk).
2. **`capri.core`**: Выделение триггерных фраз имени питомца, лемматизация и стемминг русской речи, поддержание контекста ожидания подтверждения («да/нет» для критических действий).
3. **`capri.controllers`**: Оркестратор выступает диспетчером между событиями аудио, пользовательскими окнами Qt и запуском командных сценариев.
4. **`capri.commands` & `capri.integrations`**: Изолированные обработчики действий — поиск приложений, управление питанием Windows, взаимодействие со Spotify API и Discord RPC.
5. **`capri.ui` & `capri.effects`**: Полностью процедурный интерфейс на PySide6 в кинетическом дуотоне Studio Trigger (Hot Pink / Acid Green, frameless-окна со скосами под 45°, реактивный эквалайзер Voice HUD, CRT-коллапс луча, экшен-линии и ретро-синтез речи).


---

## 4. Диаграмма последовательности Drag & Drop File Shredder (Rogue AI)

Процесс перехвата и безвозвратного поглощения файлов и папок через окно питомца под эффекты Blackwall.

```mermaid
sequenceDiagram
    autonumber
    actor User as Пользователь
    participant Window as PetWindow (Qt DnD)
    participant SFX as SpeechSFX
    participant Renderer as PetRenderer
    participant Shredder as DataShredder
    participant Speech as SpeechHUD (CyberHudBubble)

    User->>Window: dragEnterEvent (URL файлов / папок)
    Window->>SFX: play_target_acquired() (lock-on звук)
    Window->>Renderer: state.is_target_acquired = True (прицел + разряды)
    Window-->>User: acceptProposedAction()

    User->>Window: dropEvent (сброс файлов)
    Window->>Shredder: Проверка на системные пути (_is_critical_path)
    alt Попытка удалить критический системный путь
        Window->>SFX: play_lightning_strike()
        Window->>Speech: Саркастичный отказ (защита ядра ОС)
    else Пользовательские файлы и директории
        Window->>SFX: play_lightning_strike() + play_data_rip()
        Window->>Renderer: state.is_consuming = True (коллапс Blackwall)
        Window->>Shredder: shred_paths(paths) (рекурсивное безвозвратное стирание)
        Shredder-->>Window: ShredMetrics (размер, типы, количество)
        Window->>Speech: generate_shred_dialogue(metrics)
    end
```

---

## 5. Диаграмма последовательности телеметрии процессов (ProcessWatcher)

Гибридный сбор системной телеметрии активных окон (Win32) и фоновых процессов (psutil) с валидацией кулдаунов и реакцией Капри.

```mermaid
sequenceDiagram
    autonumber
    actor User as Пользователь / ОС
    participant Win32 as Win32 API (Foreground)
    participant Watcher as ProcessWatcher (QTimer)
    participant GameMode as GameModeDetector
    participant Classifier as ProcessClassifier
    participant Orch as PetOrchestrator
    participant Speech as CyberHudBubble

    User->>Win32: Переключение фокуса (напр. code.exe)
    Watcher->>Win32: GetForegroundWindow() + GetWindowThreadProcessId()
    Win32-->>Watcher: Имя процесса (code.exe)
    Watcher->>GameMode: is_game_active()?
    alt Игра активна (Game Mode)
        GameMode-->>Watcher: True
        Note over Watcher: 100% молчание, пропуск реакции
    else Обычный режим
        GameMode-->>Watcher: False
        Watcher->>Watcher: Проверка глобального дебаунса (30s) и кулдауна категории (240s)
        Watcher->>Classifier: classify("code.exe")
        Classifier-->>Watcher: category ("dev")
        Watcher->>Classifier: get_reaction_phrase("dev")
        Classifier-->>Watcher: Саркастичная реплика энграммы
        Watcher->>Orch: sig_process_context_changed("dev", "code.exe", phrase)
        Orch->>Speech: speak(phrase) + SpeechSFX
    end
```

---

## 6. Диаграмма последовательности первого появления Капри (Arasaka Biochip Hijack)

Кинематографичный оверлей первого запуска: эмуляция консоли BIOS Arasaka Relic, аварийный сбой памяти, кинетический прорыв энграммы Капри сквозь Blackwall и возможность пропуска (Esc/Space).

```mermaid
sequenceDiagram
    autonumber
    actor User as Пользователь / ОС
    participant Pet as CapriWindow
    participant Config as CapriConfig (settings.py)
    participant Effects as EffectsCoordinator
    participant Overlay as IntroBreachOverlay
    participant Screen as QScreen (Win32 Desktop)
    participant SFX as SpeechSFX
    participant Matrix as BlackwallDataStream

    User->>Pet: Запуск CapriPet (main.py)
    Pet->>Config: get_config_value("appearance.first_run_intro_completed")
    alt first_run_intro_completed == False
        Pet->>Pet: hide() (скрытие основного окна)
        Pet->>Effects: play_intro_breach(on_finished)
        Effects->>Overlay: IntroBreachOverlay(screen, sprite)
        Overlay->>Screen: grabWindow(0) (захват рабочего стола)
        Overlay->>SFX: play_intro_breach() (саундтрек BIOS + сирена + sub-bass)
        Overlay->>Overlay: Фаза 0 (0-1.0s): Терминал Arasaka Relic BIOS
        Overlay->>Overlay: Фаза 1 (1.0-1.8s): KERNEL PANIC и стробоскоп
        opt Пользователь нажал Esc или Space
            User->>Overlay: keyPressEvent (Esc / Space)
            Overlay->>Overlay: Мягкий 300мс CRT-fadeout
        end
        Overlay->>Overlay: Фаза 2 (1.8-2.6s): Вспышка, молнии и разрыв Blackwall
        Overlay->>Matrix: Отрисовка потока Blackwall сквозь разлом
        Overlay->>Overlay: Фаза 3 (2.6-4.8s): Материализация Капри + HUD реплики
        Overlay->>SFX: play_voice_success()
        Overlay->>Overlay: CRT-схлопывание в рабочий стол (fade-out)
        Overlay->>Pet: finished.emit()
        Pet->>Config: set_config_value("appearance.first_run_intro_completed", True)
        Pet->>Pet: reveal_on_startup() (показ рабочего окна на столе)
    else first_run_intro_completed == True
        Pet->>Effects: Стандартный TransitionOverlay (появление)
    end
```

---

## 7. Модель безопасности и границы доверия (Blackwall ICE)

Для предотвращения локального повышения привилегий (LPE), повреждения системных файлов Windows и исполнения произвольного кода в CapriPet реализована многоуровневая изоляция:

1. **Контур деструктивных операций (`DataShredder`, `SystemCleaner`):**
   - **Path Traversal & Symlink Defense:** Все пути нормализуются через `os.path.realpath()` и `pathlib.Path.resolve()`. Блокируются попытки передачи относительных путей (`..`), символических ссылок и точек соединения (Junctions), ведущих в системные каталоги.
   - **Черный список критических путей:** `%SystemRoot%`, `%ProgramFiles%`, `%ProgramFiles(x86)%`, `%ProgramData%`, `%WinDir%`, `%PUBLIC%`, каталоги учетных записей `C:\Users`, корни всех дисков (`C:\`, `D:\`), UNC-пути (`\\server\share`) и альтернативные потоки данных NTFS (ADS `file.txt:stream`).
   - **Изоляция очистки временных файлов:** Модуль `SystemCleaner` гарантирует, что удаление происходит строго внутри канонических границ каталогов `%TEMP%` (`is_relative_to`), а симлинки удаляются без перехода по ним.

2. **Контур внешних вызовов и сети (`AppLauncher`, `WebSearch`):**
   - **Белый список расширений:** Разрешен запуск только проверенных исполняемых файлов (`.exe`, `.lnk`). Прямой запуск опасных сценариев (`.bat`, `.cmd`, `.vbs`, `.ps1`, `.scr`) заблокирован.
   - **Сетевые шлюзы (`safe_open_url`):** Открытие ссылок в браузере ограничено исключительно веб-схемами (`http://`, `https://`). Попытки вызова кастомных ОС-протоколов (`file://`, `ms-msdt:`, `calculator:`) нейтрализуются.

3. **Контур входных данных и конфигурации (`Settings`, `InputFlow`, `Registry`):**
   - **Защита от JSON-бомб:** Конфигурационный файл защищен строгим лимитом размера (`MAX_CONFIG_FILE_SIZE = 2 МБ`). При превышении размера файл считается поврежденным и сбрасывается в дефолтное безопасное состояние.
   - **DoS / ReDoS защита:** Длина входящих текстовых и распознанных ASR команд ограничена лимитом в 500 символов, предотвращая исчерпание процессорного времени при нечетком поиске (`rapidfuzz`, стемминг).

