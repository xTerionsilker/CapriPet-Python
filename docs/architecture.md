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
        ASR["recognizer.py<br/>(Vosk / Faster-Whisper ASR)"]
        Voice -->|Фреймы речи| ASR
    end

    %% Ядро обработки
    subgraph CoreSubsystem["3. Конвейер ядра (capri.core)"]
        direction TB
        WakeWord["wake_word.py<br/>(Детектор активации «Капри»)"]
        InputFlow["input_flow.py<br/>(Конвейер сессий и подтверждений)"]
        Morphology["morphology.py<br/>(Стемминг, нормализация числительных)"]
        Settings["settings.py<br/>(Pydantic v2 .capri/config.json)"]

        WakeWord --> InputFlow
        Morphology -.-> InputFlow
    end

    %% Контроллеры и оркестрация
    subgraph Controllers["4. Контроллеры и управление (capri.controllers)"]
        direction TB
        Orchestrator["orchestrator.py<br/>(Центральный оркестратор)"]
        Inactivity["inactivity_manager.py<br/>(Таймер неактивности + PresenceReminder)"]
        ActionBridge["action_bridge.py<br/>(Асинхронный мост потоков)"]
    end

    %% Команды и интеграции
    subgraph CommandsSubsystem["5. Модульная система команд и интеграции"]
        direction TB
        Registry["commands/registry.py<br/>(Реестр и нечёткий поиск)"]
        Handlers["commands/handlers.py<br/>(Обработчики действий)"]
        Integrations["integrations/<br/>(Spotify, Discord RPC, AppLauncher, SystemControl, GameMode, Cleaner)"]

        Registry --> Handlers
        Handlers --> Integrations
    end

    %% UI и Визуальные эффекты
    subgraph VisualPresentation["6. Графический интерфейс и эффекты (capri.ui / capri.effects)"]
        direction TB
        PetWindow["ui/pet_window.py & pet_window_actions.py<br/>(Главное окно питомца, View и ActionDelegate)"]
        PetRenderer["ui/pet_renderer.py<br/>(Рендерер спрайтов, глитч-ауры Blackwall и сканлайнов)"]
        ContextMenu["ui/context_menu.py<br/>(Кибер-меню и настройки)"]
        VoiceCoord["ui/voice_coordinator.py<br/>(Координатор ASR & HUD)"]
        VoiceHUD["ui/voice_hud.py<br/>(Cyberpunk Voice HUD над taskbar)"]
        SpeechHUD["ui/speech.py & speech_sfx.py<br/>(CyberHudBubble и синтез SFX)"]
        GameOverlay["ui/game_overlay.py<br/>(SilentPresenceGlyph оверлей)"]
        Effects["effects/effects_coordinator.py<br/>(CRT-глитчи, молнии, переходы)"]

        PetWindow --> PetRenderer
        PetWindow --> ContextMenu
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
    participant UI as UI & Effects (HUD)

    User->>Voice: «Капри, запусти блокнот»
    Voice->>ASR: Аудио-чанкер (активность речи)
    ASR->>Core: Распознанная строка («капри запусти блокнот»)
    Core->>Core: Детекция триггера «капри» + нормализация
    Core->>Orch: Команда: «запусти блокнот»
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
5. **`capri.ui` & `capri.effects`**: Полностью процедурный киберпанк-интерфейс на PySide6 (frameless-окна с прозрачностью, CRT-сканлайны, синтез речи в духе ретро-консолей, HUD-индикаторы).
