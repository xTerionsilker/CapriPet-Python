@echo off
setlocal
cd /d "%~dp0\.."

echo [CAPRI] Installing Git Pre-Push Hooks...

git config core.hooksPath .githooks
if errorlevel 1 (
    echo [ERROR] Failed to set core.hooksPath via git config.
    exit /b 1
)

if exist ".git\hooks" (
    copy /Y ".githooks\pre-push" ".git\hooks\pre-push" >nul 2>&1
)

echo [OK] Git hooks successfully installed and linked to .githooks/
echo [OK] Every 'git push' will now automatically verify Ruff, Compileall, Mypy and Tests.
pause
