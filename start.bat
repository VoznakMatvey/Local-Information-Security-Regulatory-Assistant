@echo off
chcp 65001 >nul
title НПА ИБ Помощник
echo ========================================
echo   Запуск локальной ВОС для НПА ИБ
echo ========================================
echo.

cd /d "%~dp0"

:: Поиск Python через py launcher (компактно и надёжно)
where py >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден. Установите Python 3.12 с python.org
    pause
    exit /b 1
)
set "PYTHON_CMD=py"
echo [OK] Используется Python через py launcher

:: Отладочный режим (установите true для вывода Markdown первой страницы PDF и false для отключения)
set RAG_DEBUG=false

:: Установка зависимостей
echo.
echo [1/3] Установка зависимостей из requirements.txt...
%PYTHON_CMD% -m pip install --quiet --upgrade pip

:: Пробуем установить через зеркало Яндекса (быстро)
%PYTHON_CMD% -m pip install --timeout 120 --retries 5 --quiet -r requirements.txt -i https://mirror.yandex.ru/pypi/simple/

:: Проверяем, установился ли pdfplumber (как индикатор проблемных пакетов)
%PYTHON_CMD% -c "import pdfplumber" >nul 2>&1
if errorlevel 1 (
    echo [ВНИМАНИЕ] Некоторые пакеты не установились через зеркало.
    echo          Пробуем установить напрямую с PyPI...
    %PYTHON_CMD% -m pip install --timeout 120 --retries 5 --quiet -r requirements.txt -i https://pypi.org/simple/
) else (
    echo [OK] Зависимости установлены через зеркало Яндекса
)

:: Запуск Ollama
echo.
echo [2/3] Запуск Ollama...
start "Ollama Server" cmd /k "ollama.exe serve"

:: Ожидание готовности Ollama
echo Ожидание запуска Ollama...
set /a attempts=0
:wait_ollama
timeout /t 2 /nobreak > nul
curl -s http://127.0.0.1:11434/api/tags > nul 2>&1
if errorlevel 1 (
    set /a attempts+=1
    if %attempts% lss 15 goto wait_ollama
    echo [ПРЕДУПРЕЖДЕНИЕ] Ollama не отвечает. Проверьте окно с сервером.
    echo Нажмите любую клавишу для продолжения...
    pause > nul
) else (
    echo [OK] Ollama запущен и отвечает
)

:: Проверка моделей
echo Проверка моделей...
ollama.exe pull gemma4:e4b > nul 2>&1
ollama.exe pull bge-m3 > nul 2>&1

echo.
echo [3/3] Запуск Streamlit приложения...
echo ========================================
echo   Система запущена!
echo   Откройте в браузере: http://localhost:8501
echo ========================================
echo.

%PYTHON_CMD% -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

pause