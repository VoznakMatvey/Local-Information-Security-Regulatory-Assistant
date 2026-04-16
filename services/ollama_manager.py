import subprocess
import os
import time
import requests
from pathlib import Path
from config import OLLAMA_DIR, OLLAMA_HOST, OLLAMA_MODEL

class OllamaManager:
    """Управляет жизненным циклом Ollama процесса"""
    
    def __init__(self):
        self.process = None
        self.ollama_exe = OLLAMA_DIR / "ollama.exe"
        
    def start(self) -> bool:
        """Запускает Ollama сервер в фоне"""
        if self.is_running():
            print("Ollama уже запущен")
            return True
        
        if not self.ollama_exe.exists():
            raise FileNotFoundError(f"Ollama не найден по пути {self.ollama_exe}")
        
        # Устанавливаем переменные окружения для портабельности
        env = os.environ.copy()
        env["OLLAMA_HOST"] = OLLAMA_HOST
        env["OLLAMA_MODELS"] = str(OLLAMA_DIR / "models")
        
        # Запускаем в фоне
        self.process = subprocess.Popen(
            [str(self.ollama_exe), "serve"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW  # Windows: без консольного окна
        )
        
        # Ждём, пока сервер поднимется
        for _ in range(30):
            if self.is_running():
                print("✅ Ollama сервер запущен")
                return True
            time.sleep(1)
        
        return False
    
    def is_running(self) -> bool:
        """Проверяет доступность Ollama API"""
        try:
            resp = requests.get(f"http://{OLLAMA_HOST}/api/tags", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def pull_model(self) -> bool:
        """Скачивает модель, если её нет локально"""
        if not self.is_running():
            raise RuntimeError("Ollama не запущен")
        
        # Проверяем, есть ли модель
        resp = requests.get(f"http://{OLLAMA_HOST}/api/tags")
        models = resp.json().get("models", [])
        model_names = [m["name"].split(":")[0] for m in models]
        
        if OLLAMA_MODEL.split(":")[0] in model_names:
            print(f"✅ Модель {OLLAMA_MODEL} уже установлена")
            return True
        
        print(f"📥 Скачивание модели {OLLAMA_MODEL} (впервые — потребуется интернет)...")
        
        # Запускаем pull
        subprocess.run(
            [str(self.ollama_exe), "pull", OLLAMA_MODEL],
            check=True
        )
        print(f"✅ Модель {OLLAMA_MODEL} загружена")
        return True
    
    def stop(self):
        """Останавливает Ollama процесс"""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=10)
            self.process = None
            print("Ollama остановлен")
