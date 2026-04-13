@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Создаю виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Не удалось создать виртуальное окружение.
        pause
        exit /b 1
    )
)

echo [INFO] Обновляю зависимости...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Не удалось установить зависимости.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [WARN] Файл .env не найден.
    echo [WARN] Скопируйте .env.example в .env и заполните настройки.
    pause
    exit /b 1
)

echo [INFO] Запускаю бота...
".venv\Scripts\python.exe" bot.py

echo.
echo [INFO] Бот завершил работу.
pause
