## Summary
<!-- Краткий технический обзор функционала, архитектурное обоснование и лор-интеграция -->

## What's Changed
<!-- Структурированный список изменений по подсистемам с выделением ключевых компонентов -->
- **Component / Subsystem**:
  - Details

## Merge Requirements
> [!IMPORTANT]
> **Обязательное условие слияния (Merge Gate):**
> Для слияния пулл-реквеста в ветку `main` требуется успешное прохождение локальной верификации `scripts\verify.bat --report-status` с зарегистрированным статусом коммита **`Local CI / Integrity` [success]**. Слияние без этого статуса заблокировано на уровне правил защиты ветки (Branch Protection).

## Verification & Tests
<!-- Чекбокс-лист пройденных проверок -->
- [ ] Обязательная локальная верификация пройдена (`scripts\verify.bat --report-status`)
- [ ] Линтер: `.\.venv\Scripts\ruff.exe check .`
- [ ] Байткод-компиляция: `compileall` без ошибок (`capri`, `scripts`, `main.py`)
- [ ] Статический анализ типов: `.\.venv\Scripts\mypy.exe capri`
- [ ] Набор тестов: `.\.venv\Scripts\python.exe -m unittest discover -s tests`
- [ ] SAST & зависимости: Bandit SAST и pip-audit
