"""
Управление эмбеддинг-моделями через Ollama (без Hugging Face)
Не требует скачивания моделей с Hugging Face, использует локальный Ollama
"""

import logging
from typing import Optional, List, Any
from pathlib import Path

from langchain_community.embeddings import OllamaEmbeddings

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """
    Управляет эмбеддинг-моделями через Ollama.
    """
    
    AVAILABLE_MODELS = {
        "nomic_embed": {
            "name": "nomic-embed-text",
            "dimension": 768,
            "size_mb": 270,
            "description": "Лучшая для эмбеддингов, многоязычная"
        },
        "all_minilm": {
            "name": "all-minilm",
            "dimension": 384,
            "size_mb": 150,
            "description": "Лёгкая и быстрая"
        },
        "bge_m3": {
            "name": "bge-m3",
            "dimension": 1024,
            "size_mb": 500,
            "description": "Высокое качество, многоязычная"
        }
    }
    
    def __init__(self, 
                 model_name: str = "bge_m3",   # изменено с nomic_embed на bge_m3
                 cache_folder: Optional[Path] = None,
                 device: str = "cpu",
                 ollama_host: str = "http://127.0.0.1:11434"):
        self.cache_folder = Path(cache_folder) if cache_folder else Path("./models_cache")
        self.device = device
        
        if model_name in self.AVAILABLE_MODELS:
            self.model_full_name = self.AVAILABLE_MODELS[model_name]["name"]
        else:
            self.model_full_name = model_name
            
        self.ollama_host = ollama_host
        self._embeddings = None
        
        logger.info(f"Инициализация эмбеддинг-модели Ollama: {self.model_full_name}")
        print(f"📥 Используем Ollama для эмбеддингов: {self.model_full_name}")
        print(f"   Адрес Ollama: {ollama_host}")
    
    def get_embeddings(self) -> OllamaEmbeddings:
        return self.embeddings
        
    @property
    def embeddings(self) -> OllamaEmbeddings:
        if self._embeddings is None:
            try:
                self._embeddings = OllamaEmbeddings(
                    model=self.model_full_name,
                    base_url=self.ollama_host,
                )
                logger.info("✅ Ollama эмбеддинги загружены")
                print("✅ Ollama эмбеддинги готовы к работе")
            except Exception as e:
                logger.error(f"Ошибка загрузки эмбеддингов: {e}")
                print(f"❌ Ошибка: {e}")
                print(f"   Убедитесь, что Ollama запущен и модель скачана: ollama pull {self.model_full_name}")
                raise
        return self._embeddings
    
    def encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        if not texts:
            return []
        try:
            return self.embeddings.embed_documents(texts)
        except Exception as e:
            logger.error(f"Ошибка при кодировании текстов: {e}")
            raise
    
    def encode_query(self, query: str) -> List[float]:
        if not query:
            return []
        try:
            return self.embeddings.embed_query(query)
        except Exception as e:
            logger.error(f"Ошибка при кодировании запроса: {e}")
            raise
    
    def get_model_info(self) -> dict:
        model_key = None
        for key, value in self.AVAILABLE_MODELS.items():
            if value["name"] == self.model_full_name:
                model_key = key
                break
        return {
            "model_key": model_key or "custom",
            "model_name": self.model_full_name,
            "dimension": self.AVAILABLE_MODELS.get(model_key, {}).get("dimension", "unknown"),
            "provider": "Ollama",
            "ollama_host": self.ollama_host
        }
    
    def check_model_available(self) -> bool:
        try:
            import requests
            resp = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m["name"].split(":")[0] for m in models]
                return self.model_full_name.split(":")[0] in model_names
            return False
        except Exception as e:
            logger.error(f"Ошибка проверки модели: {e}")
            return False
    
    def clear_cache(self):
        self._embeddings = None
        logger.info("Кэш эмбеддингов очищен")
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear_cache()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # быстрый тест
    emb = EmbeddingsManager()
    print(emb.get_model_info())
