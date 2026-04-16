import os
from pathlib import Path

# Базовые пути
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "laws"
CHROMA_DIR = BASE_DIR / "chroma_db"
OLLAMA_DIR = BASE_DIR / "ollama"
MODELS_CACHE = BASE_DIR / "models_cache"

# Настройки Ollama
OLLAMA_HOST = "127.0.0.1:11434"
OLLAMA_MODEL = "gemma4:e4b"
OLLAMA_TIMEOUT = 120

# Настройки эмбеддингов (для обычного RAG)
EMBEDDING_MODEL = "bge-m3"

# RAPTOR настройки (пока не используются)
RAPTOR_EMBEDDING_MODEL = "bge-m3"

# ========== НАСТРОЙКИ ФИКСИРОВАННОГО ЧАНКИНГА ==========
CHUNK_SIZE = 2048          # размер чанка в символах (примерно 500-700 токенов)
CHUNK_OVERLAP = 200        # перекрытие между чанками
CHUNK_SEPARATORS = ["\n\n", "\n", ".", " ", ""]  # разделители для RecursiveCharacterTextSplitter

# ========== НАСТРОЙКИ ПОИСКА ==========
RETRIEVAL_TOP_K = 5        # сколько чанков ищем изначально
NEIGHBOUR_CHUNKS = 1       # сколько соседних чанков добавляем к каждому найденному (слева и справа)
SIMILARITY_THRESHOLD = 0.7
USE_HYBRID_SEARCH = True   # включаем гибридный поиск (BM25 + векторный)
BM25_WEIGHT = 0.5          # вес BM25 в ансамбле
VECTOR_WEIGHT = 0.5        # вес векторного поиска
USE_MMR = False

# ========== НАСТРОЙКИ ГЕНЕРАЦИИ ==========
TEMPERATURE = 0.3
MAX_TOKENS = 4096
SYSTEM_PROMPT = """Ты — эксперт по информационной безопасности и нормативно-правовым актам РФ.
Отвечай строго на основе предоставленных фрагментов документов.
Если информация отсутствует в документах, прямо скажи: «В предоставленных НПА нет информации по этому вопросу».
Всегда указывай источник (название документа и статью/раздел, если возможно).
Используй простой и понятный язык, избегай юридических терминов без необходимости.
"""

# Создаём необходимые папки
for dir_path in [DATA_DIR, CHROMA_DIR, OLLAMA_DIR, MODELS_CACHE]:
    dir_path.mkdir(parents=True, exist_ok=True)