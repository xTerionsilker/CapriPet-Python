#Requires -Version 5.1
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       CapriPet C# WPF - Установка и настройка" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Проверка .NET SDK
try {
    $dotnetVersion = & dotnet --version
    Write-Host "[OK] .NET SDK обнаружен (версия: $dotnetVersion)" -ForegroundColor Green
}
catch {
    Write-Host "[ОШИБКА] .NET SDK не найден в PATH!" -ForegroundColor Red
    Write-Host "Пожалуйста, установите .NET SDK 8, 9 или 11: https://dotnet.microsoft.com/download" -ForegroundColor Yellow
    exit 1
}

# 2. Директории и пути
$projectRoot = $PSScriptRoot
if (-not $projectRoot) { $projectRoot = Get-Location }

$modelsDir = Join-Path $projectRoot "Assets\Models"
if (-not (Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
}

$modelFile = Join-Path $modelsDir "ggml-base.bin"
$modelTmp = Join-Path $modelsDir "ggml-base.bin.tmp"
$modelUrl = "https://huggingface.co/sandrohanea/whisper.net/resolve/v2/classic/ggml-base.bin"
$minExpectedBytes = 145000000

# 3. Проверка модели Whisper
$needDownload = $true

if (Test-Path $modelFile) {
    $fileSize = (Get-Item $modelFile).Length
    Write-Host "Обнаружен локальный файл модели: $fileSize байт." -ForegroundColor Gray
    
    if ($fileSize -ge $minExpectedBytes) {
        Write-Host "[OK] Модель Whisper ggml-base.bin проверена и готова к работе." -ForegroundColor Green
        $needDownload = $false
    }
    else {
        Write-Host "[ВНИМАНИЕ] Файл модели поврежден или недокачан ($fileSize байт из ~147 МБ)." -ForegroundColor Yellow
        Write-Host "Удаление поврежденного файла..." -ForegroundColor Yellow
        Remove-Item $modelFile -Force -ErrorAction SilentlyContinue
    }
}

# 4. Скачивание модели при необходимости
if ($needDownload) {
    Write-Host ""
    Write-Host "[СКАЧИВАНИЕ] Загрузка модели Whisper (русский язык, ~147 МБ)..." -ForegroundColor Yellow
    Write-Host "URL: $modelUrl" -ForegroundColor Gray

    if (Test-Path $modelTmp) {
        Remove-Item $modelTmp -Force -ErrorAction SilentlyContinue
    }

    $curlAvailable = (Get-Command curl.exe -ErrorAction SilentlyContinue) -ne $null
    if ($curlAvailable) {
        & curl.exe -L --progress-bar -o $modelTmp $modelUrl
    }
    else {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($modelUrl, $modelTmp)
    }

    if (Test-Path $modelTmp) {
        $downloadedSize = (Get-Item $modelTmp).Length
        if ($downloadedSize -ge $minExpectedBytes) {
            Move-Item -Path $modelTmp -Destination $modelFile -Force
            Write-Host "[OK] Модель успешно скачана и проверена ($downloadedSize байт)." -ForegroundColor Green
        }
        else {
            Remove-Item $modelTmp -Force -ErrorAction SilentlyContinue
            Write-Host "[ОШИБКА] Файл скачался не полностью ($downloadedSize байт)." -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Host "[ОШИБКА] Не удалось сохранить файл модели." -ForegroundColor Red
        exit 1
    }
}

# 5. Сборка проекта
Write-Host ""
Write-Host "[СБОРКА] Восстановление NuGet-пакетов и сборка проекта..." -ForegroundColor Cyan
& dotnet restore
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ОШИБКА] Сбой при dotnet restore." -ForegroundColor Red
    exit 1
}

& dotnet build -c Debug
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ОШИБКА] Сбой при dotnet build." -ForegroundColor Red
    exit 1
}

# Копирование модели в билд-папку
$binModelsDir = Join-Path $projectRoot "bin\Debug\net11.0-windows\Assets\Models"
if (-not (Test-Path $binModelsDir)) {
    New-Item -ItemType Directory -Path $binModelsDir -Force | Out-Null
}
Copy-Item -Path $modelFile -Destination (Join-Path $binModelsDir "ggml-base.bin") -Force

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "       [УСПЕХ] CapriPet полностью настроен и готов!    " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Для запуска используйте: dotnet run" -ForegroundColor Yellow

$choice = Read-Host "Запустить CapriPet прямо сейчас? (Y/n)"
if ($choice -match "^[yY]?$") {
    Write-Host "Запуск CapriPet..." -ForegroundColor Cyan
    & dotnet run
}
