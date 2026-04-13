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
    if exist ".env.example" (
        echo [INFO] Файл .env не найден — создаю из .env.example ...
        copy /Y ".env.example" ".env" >nul
        echo [INFO] Файл .env создан. Откройте его в блокноте и заполните:
        echo       BOT_TOKEN, SOURCE_CHAT_IDS, TARGET_CHAT_ID
        echo       ^(ORDER_KEYWORDS — по желанию^)
        echo.
        echo [INFO] После сохранения снова запустите run.bat
    ) else (
        echo [ERROR] Нет ни .env, ни .env.example. Восстановите файлы из репозитория.
    )
    pause
    exit /b 1
)

echo [INFO] Запускаю бота...
".venv\Scripts\python.exe" bot.py

echo.
echo [INFO] Бот завершил работу.
pause
