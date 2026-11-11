@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv not found. Please run scripts\setup_env.bat first.
    exit /b 1
)

set "RUN_CONSOLE=0"
set "PASSTHROUGH_ARGS="

:parse_loop
if "%~1"=="" goto run_app

if /i "%~1"=="--console" (
    set "RUN_CONSOLE=1"
    shift
    goto parse_loop
)

if /i "%~1"=="--debug" (
    set "RUN_CONSOLE=1"
    shift
    goto parse_loop
)

set "PASSTHROUGH_ARGS=!PASSTHROUGH_ARGS! %1"
shift
goto parse_loop

:run_app
if "!RUN_CONSOLE!"=="1" (
    echo [INFO] Launching CapriPet in attached console mode...
    ".venv\Scripts\python.exe" main.py !PASSTHROUGH_ARGS!
) else (
    echo [INFO] Launching CapriPet in windowless background mode...
    start "" ".venv\Scripts\pythonw.exe" main.py !PASSTHROUGH_ARGS!
)

if !errorlevel! neq 0 (
    echo [ERROR] CapriPet launch failed with error code !errorlevel!.
    exit /b !errorlevel!
)

exit /b 0
