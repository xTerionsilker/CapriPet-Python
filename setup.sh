#!/usr/bin/env bash
set -e

echo "========================================================"
echo "       CapriPet C# WPF - Установка и настройка"
echo "========================================================"
echo ""

# 1. Проверка .NET SDK
if ! command -v dotnet &> /dev/null; then
    echo "[ОШИБКА] .NET SDK не найден в PATH!"
    echo "Пожалуйста, установите .NET SDK 8, 9 или 11: https://dotnet.microsoft.com/download"
    exit 1
fi

DOTNET_VER=$(dotnet --version)
echo "[OK] .NET SDK обнаружен (версия: $DOTNET_VER)"

# 2. Пути
MODELS_DIR="Assets/Models"
mkdir -p "$MODELS_DIR"

MODEL_FILE="$MODELS_DIR/ggml-base.bin"
MODEL_TMP="$MODELS_DIR/ggml-base.bin.tmp"
MODEL_URL="https://huggingface.co/sandrohanea/whisper.net/resolve/v2/classic/ggml-base.bin"
MIN_BYTES=145000000

# 3. Проверка модели Whisper
NEED_DOWNLOAD=false

if [ -f "$MODEL_FILE" ]; then
    FILE_SIZE=$(wc -c < "$MODEL_FILE" | tr -d ' ')
    echo "Обнаружен локальный файл модели: $FILE_SIZE байт."
    if [ "$FILE_SIZE" -lt "$MIN_BYTES" ]; then
        echo "[ВНИМАНИЕ] Файл поврежден или недокачан ($FILE_SIZE байт из ~147 МБ)."
        rm -f "$MODEL_FILE"
        NEED_DOWNLOAD=true
    else
        echo "[OK] Модель Whisper ggml-base.bin проверена."
    fi
else
    NEED_DOWNLOAD=true
fi

# 4. Скачивание при необходимости
if [ "$NEED_DOWNLOAD" = true ]; then
    echo ""
    echo "[СКАЧИВАНИЕ] Загрузка модели Whisper (русский язык, ~147 МБ)..."
    rm -f "$MODEL_TMP"

    if command -v curl &> /dev/null; then
        curl -L --progress-bar -o "$MODEL_TMP" "$MODEL_URL"
    elif command -v wget &> /dev/null; then
        wget -O "$MODEL_TMP" "$MODEL_URL"
    else
        echo "[ОШИБКА] Ни curl, ни wget не найдены!"
        exit 1
    fi

    TMP_SIZE=$(wc -c < "$MODEL_TMP" | tr -d ' ')
    if [ "$TMP_SIZE" -ge "$MIN_BYTES" ]; then
        mv "$MODEL_TMP" "$MODEL_FILE"
        echo "[OK] Модель успешно скачана и проверена."
    else
        echo "[ОШИБКА] Скачивание не завершилось полностью ($TMP_SIZE байт)."
        rm -f "$MODEL_TMP"
        exit 1
    fi
fi

# 5. Сборка проекта
echo ""
echo "[СБОРКА] Восстановление NuGet-пакетов и компиляция проекта..."
dotnet restore
dotnet build -c Debug

# Копирование модели в билд-папку для надежности
DEBUG_TARGET="bin/Debug/net11.0-windows/Assets/Models"
mkdir -p "$DEBUG_TARGET"
cp -f "$MODEL_FILE" "$DEBUG_TARGET/ggml-base.bin" 2>/dev/null || true

echo ""
echo "========================================================"
echo "       [УСПЕХ] CapriPet полностью настроен и готов!"
echo "========================================================"
echo "Для запуска выполните: dotnet run"
