@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0\.."

REM Check if virtual environment already exists
if exist ".venv\Scripts\python.exe" (
    echo [INFO] Python virtual environment .venv already exists.
    exit /b 0
)

echo [INFO] Virtual environment .venv not found. Initializing...

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
    echo [ERROR] Python not found in system! Please install Python 3.10+ and add it to PATH.
    exit /b 1
)

"!PY_CMD!" -m venv .venv
if !errorlevel! neq 0 (
    echo [ERROR] Failed to create virtual environment .venv.
    exit /b 1
)

echo [INFO] Virtual environment .venv successfully created.
exit /b 0
