# Структура проекта CapriPet

```text
main.py                         # Главная точка входа приложения
capriWin.bat                    # Фасад-оркестратор быстрого запуска для Windows
version.txt                     # Текущая версия приложения
scripts/                        # Модульные скрипты подготовки и запуска
├── download_models.py          # Загрузка и проверка моделей Silero VAD и Vosk ASR
├── install_deps.bat            # Проверка и установка зависимостей из requirements.txt
├── run_app.bat                 # Запуск приложения (фоновый режим / консоль через --console)
└── setup_env.bat               # Проверка системного Python и создание виртуального окружения .venv
capri/
├── __init__.py
├── audio/                      # Голосовой ввод и распознавание речи
│   ├── recognizer.py           # Распознавание речи (монопольный Vosk ASR)
│   ├── sfx_generators.py       # Процедурный синтез аудио-форм волны и PCM DSP (без Qt)
│   └── voice.py                # Захват аудио с микрофона и VAD (Silero)
├── commands/                   # Модульная система команд
│   ├── __init__.py             # Центральный список команд и фабрика реестра
│   ├── apps.py                 # Обработчики команд запуска и завершения процессов Windows
│   ├── base.py                 # BaseCommand, CommandContext, CommandResult
│   ├── debug.py                # Диагностика, телеметрия ядра, переключение глитчей и поиск мыши
│   ├── handlers.py             # Фасад ре-экспорта всех стандартных команд (обратная совместимость)
│   ├── media.py                # Обработчики команд медиаплеера Spotify
│   ├── registry.py             # Реестр команд, нечёткий поиск, переключение раскладки
│   ├── system.py               # Команды питания, блокировки экрана, очистки диска и аудита реестра
│   ├── volume.py               # Команды прямого контроля мастер-громкости Windows
│   └── web.py                  # Обработчики веб-поиска в Google и YouTube
├── controllers/                # Контроллеры логики и жизненного цикла
│   ├── action_bridge.py        # Мост асинхронных операций между UI и интеграциями
│   ├── inactivity_manager.py   # Таймер неактивности и напоминания о присутствии
│   ├── orchestrator.py         # Центральный оркестратор логики: связь команд, аудио и UI
│   └── process_watcher.py      # Гибридный мониторинг активных и фоновых процессов Windows
├── core/                       # Ядро распознавания, конвейер и настройки
│   ├── __init__.py
│   ├── input_flow.py           # Конвейер обработки ввода и подтверждения команд
│   ├── morphology.py           # Стемминг русской морфологии и парсер числительных
│   ├── process_classifier.py   # Семантический классификатор процессов и контекстные реплики
│   ├── settings.py             # Сохранение настроек config.json и генерация User-Agent
│   └── wake_word.py            # Детектор активационной фразы («Капри») и нечёткий поиск
├── effects/                    # Визуальные эффекты и анимации
│   ├── __init__.py
│   ├── blackwall_data_stream.py # Процедурный генератор вертикального дампа памяти Blackwall
│   ├── cursor_pointer.py       # Эффект прицеливания молниями на позицию курсора мыши
│   ├── effects_coordinator.py  # Фасад управления эффектами, глитчами и оверлеями
│   ├── engram_prank_coordinator.py # Координатор пасхалок энграммы, двухступенчатых шансов и кулдаунов
│   ├── glitch.py               # CRT/ЭЛТ-глитч-оверлей и алгоритмы искажений
│   ├── intro_breach_helpers.py # Процедурные отрисовщики BIOS Arasaka, KERNEL PANIC, HUD и молний интро
│   ├── intro_breach_overlay.py # Кинематографичный оверлей первого запуска с перехватом биочипа и пропуском
│   ├── lightning_tether.py     # Оверлей прицеливания молнией при перемещении Капри
│   ├── melting_screen.py       # Процедурный вирусный оверлей тающего экрана (Melting Screen Glitch)
│   ├── model_init_animation.py # HUD-анимация инициализации модели Vosk при запуске
│   ├── relic_dump_overlay.py   # Киберпанк-оверлей мини-терминала сбоя памяти биочипа Relic
│   ├── session_anim_helpers.py # Вспомогательные отрисовщики сессионных кибер-анимаций
│   ├── session_animations.py   # Киберпанк-анимации перед системными действиями
│   ├── transition_base.py      # Базовые цветовые константы и утилиты процедурных переходов
│   ├── transition_modes.py     # Отрисовщики режимов появления, скрытия и стелса
│   ├── transition_painters.py  # Процедурные отрисовщики геометрических траекторий и молний
│   ├── transition.py           # Процедурная кибер-анимация скрытия/появления
│   └── transition_fx.py        # Палитра, шины и кадры эффекта перехода-молнии
├── integrations/               # Внешние интеграции и системные команды
│   ├── __init__.py
│   ├── app_launcher.py         # Поиск и запуск установленных приложений Windows
│   ├── data_shredder.py        # Безвозвратное уничтожение файлов/папок и сарказм-диалоги энграммы
│   ├── discord_rpc.py          # Discord Rich Presence (статус, ASR модель, таймер, кнопка)
│   ├── process_manager.py      # Мониторинг, группировка и завершение процессов
│   ├── registry_scanner.py     # Безопасный аудит реестра Windows на пустые и битые ветки с генерацией отчета
│   ├── spotify.py              # Клиент и Web API для Spotify
│   ├── system_cleaner.py       # Безопасная очистка корзины (Shell API) и временных файлов
│   ├── system_control.py       # Питание, блокировка экрана и управление курсором
│   ├── system_power_hook.py    # Win32 хуки событий питания (сон, выключение, сессии)
│   ├── system_volume.py        # Прямой контроль мастер-громкости Windows (Core Audio API / pycaw)
│   ├── game_mode.py            # Детекция полноэкранных игр через Win32 API и SHQueryUserNotificationState с фильтрацией Maximized окон
│   ├── web_search.py           # Поиск в веб-браузере и проверка обновлений
│   └── window_tracker.py       # Определение геометрии активного окна (Win32 DWM)
└── ui/                         # Графический интерфейс на PySide6 (Qt)
    ├── __init__.py
    ├── console_hud.py          # Cyber HUD терминал прямого ввода команд с кнопкой TERMINATE
    ├── context_menu.py         # Контекстное меню, стиль Cyberpunk и меню-билдер
    ├── game_overlay.py         # Компактный клиновидный HUD-индикатор режима тишины (Stealth)
    ├── pet_renderer.py         # Рендерер спрайта, сканлайны, аура и кинетические экшен-линии
    ├── pet_window.py           # Окно питомца Qt (View-слой, геометрия и события)
    ├── pet_window_actions.py   # Делегат действий и обработчиков настроек окна питомца
    ├── reminder_dialog.py      # Модальное окно настройки интервалов напоминаний в стиле Cyberpunk
    ├── shredder_drop_handler.py # Делегат Drag & Drop поглощения файлов Blackwall
    ├── speech.py               # Диалоговые HUD-облачка в дуотоне Studio Trigger с CRT-коллапсом
    ├── speech_sfx.py           # Воспроизведение звуков речи и интерфейса (QSoundEffect)
    ├── sprite_manager.py       # Менеджер загрузки, кэширования и масштабирования поз
    ├── teleport_controller.py  # Контроллер перемещения окна через наведение молнией
    ├── theme.py                # Цветовая палитра дуотона Studio Trigger, шрифты и стили UI
    ├── tray_manager.py         # Менеджер интеграции с системным треем и областью уведомлений
    ├── voice_coordinator.py    # Координация распознавания речи, триггеров и Voice HUD
    ├── voice_hud.py            # HUD голосового ввода над taskbar с реактивным эквалайзером
    └── volume_hud.py           # Cyber Audio HUD экранный оверлей регулировки системной громкости
tests/                          # Модульные и интеграционные тесты (unittest)
├── test_commands_modular.py    # Тесты модульных команд и фасада handlers
├── test_download_models.py     # Тесты загрузчика и валидатора моделей ASR/VAD
├── test_engram_pranks.py       # Тесты пасхалок энграммы, уклонения от курсора, тающего экрана и кулдаунов
├── test_game_mode.py           # Тесты детектора игрового режима и фильтрации развёрнутых окон
├── test_imports.py             # Тесты целостности импортов и UI контекстного меню
├── test_process_telemetry.py   # Тесты классификатора и телеметрии процессов
├── test_registry_scanner.py    # Тесты безопасного сканера системного реестра
├── test_security_hardening.py  # Тесты валидации URL, путей и защиты от инъекций
└── test_window_lifecycle.py   # Интеграционный Smoke-тест жизненного цикла CapriWindow
assets/                         # Графика, иконка приложения (capri_icon.png) и позы (var/)
docs/                           # Дополнительная документация и спецификации (config_spec.md, architecture.md)
models/                         # Папка моделей (Vosk, Silero VAD onnx)
requirements.txt                # Зависимости проекта
mypy.ini                        # Конфигурация статического тайп-чекера Mypy
AGENTS.md                       # Главная точка входа правил разработки для AI-агентов
LICENSE                         # Лицензия MIT
```
