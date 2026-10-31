@echo off
setlocal
cd /d "%~dp0"

REM 1. Проверяем наличие виртуального окружения
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Виртуальное окружение .venv не найдено. Создаём...
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
    ) else (
        where python >nul 2>&1
        if %errorlevel% equ 0 (
            set "PY_CMD=python"
        ) else (
            echo [ERROR] Python не найден в системе! Установите Python 3.10+ и добавьте его в PATH.
            pause
            exit /b 1
        )
    )

    "%PY_CMD%" -m venv .venv
    if errorlevel 1 (
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

endlocal
