#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Проверяем наличие виртуального окружения
if [ ! -f ".venv/bin/python" ]; then
    echo "[INFO] Виртуальное окружение .venv не найдено. Создаём..."
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
    else
        echo "[ERROR] Python не найден в системе! Установите Python 3.10+."
        exit 1
    fi

    "$PYTHON_CMD" -m venv .venv
    echo "[INFO] Окружение .venv успешно создано."
fi

# 2. Проверяем установку зависимостей
if ! ./.venv/bin/python -c "import PySide6; import vosk" >/dev/null 2>&1; then
    echo "[INFO] Необходимые библиотеки не установлены. Устанавливаем зависимости из requirements.txt..."
    ./.venv/bin/python -m pip install --upgrade pip
    ./.venv/bin/pip install -r requirements.txt
    echo "[INFO] Зависимости успешно установлены."
fi

# 3. Запуск CapriPet
exec ./.venv/bin/python main.py "$@"
