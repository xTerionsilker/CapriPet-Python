@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM 1. Проверяем наличие виртуального окружения Windows
if not exist ".venv\Scripts\python.exe" (
    if exist ".venv\bin\python" (
        echo [WARNING] Обнаружено Linux-окружение .venv. Удалите его или пересоздайте для Windows!
    )
    echo [INFO] Виртуальное окружение .venv не найдено. Создаём...
    
    set "PY_CMD="
    where py >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=py"
    ) else (
        where python >nul 2>&1
        if !errorlevel! equ 0 (
            set "PY_CMD=python"
        )
    )

    if not defined PY_CMD (
        echo [ERROR] Python не найден в системе! Установите Python 3.10+ и добавьте его в PATH.
        pause
        exit /b 1
    )

    "!PY_CMD!" -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Не удалось создать виртуальное окружение .venv.
        pause
        exit /b 1
    )
    echo [INFO] Окружение .venv успешно создано.
)

REM 2. Проверяем установку зависимостей
".venv\Scripts\python.exe" -c "import PySide6; import vosk" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Необходимые библиотеки не установлены. Устанавливаем зависимости из requirements.txt...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\pip.exe" install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Ошибка при установке зависимостей.
        pause
        exit /b 1
    )
    echo [INFO] Зависимости успешно установлены.
)

REM 3. Запуск CapriPet
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] CapriPet завершился с ошибкой (код !errorlevel!).
    pause
)

endlocal
