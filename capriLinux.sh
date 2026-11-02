#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Проверяем наличие виртуального окружения
if [ ! -f ".venv/bin/python" ]; then
    if [ -f ".venv/Scripts/python.exe" ]; then
        echo "[WARNING] Обнаружено Windows-окружение .venv! Удалите .venv перед запуском на Linux."
    fi

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

# 3. Автогенерация ярлыка на рабочем столе и в меню приложений
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
ICON_PATH="$SCRIPT_DIR/assets/capri_icon.png"

create_desktop_entry() {
    local target_file="$1"
    cat <<EOF > "$target_file"
[Desktop Entry]
Type=Application
Name=CapriPet
Comment=Capri Desktop Pet
Exec=$SCRIPT_DIR/capriLinux.sh
Icon=$ICON_PATH
Path=$SCRIPT_DIR
Terminal=false
Categories=Utility;Game;
StartupNotify=false
EOF
    chmod +x "$target_file"
}

# Ярлык на Рабочем столе
if [ -d "$DESKTOP_DIR" ] && [ ! -f "$DESKTOP_DIR/CapriPet.desktop" ]; then
    create_desktop_entry "$DESKTOP_DIR/CapriPet.desktop"
    # Для сред GNOME разрешаем запуск ярлыка, если gio доступен
    gio set "$DESKTOP_DIR/CapriPet.desktop" metadata::trusted true 2>/dev/null || true
    echo "[INFO] Создан ярлык на рабочем столе: $DESKTOP_DIR/CapriPet.desktop"
fi

# Ярлык в меню приложений пользователя (~/.local/share/applications)
USER_APPS_DIR="$HOME/.local/share/applications"
if [ ! -f "$USER_APPS_DIR/CapriPet.desktop" ]; then
    mkdir -p "$USER_APPS_DIR"
    create_desktop_entry "$USER_APPS_DIR/CapriPet.desktop"
    echo "[INFO] Создан ярлык в меню приложений: $USER_APPS_DIR/CapriPet.desktop"
fi

# 4. Запуск CapriPet
set +e
./.venv/bin/python main.py "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo
    echo "[ERROR] CapriPet завершился с ошибкой (код $EXIT_CODE)."
    if [ -t 0 ] && [ -t 1 ]; then
        read -r -p "Нажмите Enter для выхода..." dummy 2>/dev/null || true
    fi
    exit $EXIT_CODE
fi
