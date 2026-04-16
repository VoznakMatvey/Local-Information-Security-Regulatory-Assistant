@echo off
chcp 65001 >nul
title НПА ИБ Помощник
echo ========================================
echo   Запуск локальной ВОС для НПА ИБ
echo ========================================
echo.

cd /d "%~dp0"

:: Поиск Python 3.12
set "PYTHON_CMD="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    set "PYTHON_SCRIPTS=%LOCALAPPDATA%\Programs\Python\Python312\Scripts"
) else if exist "%ProgramFiles%\Python312\python.exe" (
    set "PYTHON_CMD=%ProgramFiles%\Python312\python.exe"
    set "PYTHON_SCRIPTS=%ProgramFiles%\Python312\Scripts"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    set "PYTHON_SCRIPTS=%LOCALAPPDATA%\Programs\Python\Python313\Scripts"
) else if exist "%ProgramFiles%\Python313\python.exe" (
    set "PYTHON_CMD=%ProgramFiles%\Python313\python.exe"
    set "PYTHON_SCRIPTS=%ProgramFiles%\Python313\Scripts"
) else (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ОШИБКА] Python не найден. Установите Python 3.12 с python.org
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py -3.12"
    set "PYTHON_SCRIPTS="
)

if defined PYTHON_CMD (
    echo [OK] Используется Python: %PYTHON_CMD%
    if defined PYTHON_SCRIPTS (
        set "PATH=%PYTHON_SCRIPTS%;%PATH%"
        echo [OK] Добавлен путь: %PYTHON_SCRIPTS%
    )
)

:: Настройка зеркала Яндекса
pip config set global.index-url https://mirror.yandex.ru/pypi/simple/ >nul 2>&1

echo [1/4] Установка Cython...
%PYTHON_CMD% -m pip install --quiet cython

echo [2/4] Установка основных зависимостей...
%PYTHON_CMD% -m pip install --timeout 120 --retries 5 --quiet streamlit langchain langchain-community langchain-chroma chromadb sentence-transformers pypdf docx2txt2 python-docx unstructured requests numpy

echo [3/4] Установка пакетов RAPTOR...
%PYTHON_CMD% -m pip install --timeout 120 --retries 5 --quiet llama-index-packs-raptor llama-index-llms-ollama llama-index-embeddings-ollama llama-index-vector-stores-chroma rank_bm25 --index-url https://pypi.org/simple/

:: Запуск Ollama в отдельном окне
echo [4/4] Запуск Ollama...
echo Запуск Ollama в новом окне...
start "Ollama Server" cmd /k "ollama.exe serve"

:: Ожидаем готовности Ollama (до 30 секунд)
echo Ожидание запуска Ollama...
set /a attempts=0
:wait_ollama
timeout /t 2 /nobreak > nul
curl -s http://127.0.0.1:11434/api/tags > nul 2>&1
if errorlevel 1 (
    set /a attempts+=1
    if %attempts% lss 15 goto wait_ollama
    echo [ПРЕДУПРЕЖДЕНИЕ] Ollama не отвечает. Проверьте окно с сервером.
    echo Вы можете продолжить, но индексация может быть медленной.
    echo Нажмите любую клавишу для продолжения...
    pause > nul
) else (
    echo [OK] Ollama запущен и отвечает
)

:: Проверка и загрузка моделей (только отсутствующих)
echo Проверка моделей...
set "MODELS=gemma4:e4b bge-m3"
for %%m in (%MODELS%) do (
    ollama list | find "%%m" > nul
    if errorlevel 1 (
        echo Скачивание модели %%m...
        ollama pull %%m > nul 2>&1
    ) else (
        echo Модель %%m уже установлена
    )
)

echo.
echo ========================================
echo   Система запущена!
echo   Откройте в браузере: http://localhost:8501
echo ========================================
echo.

%PYTHON_CMD% -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

pause