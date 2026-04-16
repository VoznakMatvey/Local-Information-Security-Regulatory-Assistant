"""
Services module for Local Law QA system
Содержит всю бизнес-логику системы
"""

# Импортируем основные классы для удобного доступа
from services.document_processor import DocumentProcessor
from services.chunker import SmartChunker
from services.embeddings_ollama import EmbeddingsManager  
from services.vector_store import VectorStoreManager
# from services.retriever import HybridRetriever
from services.rag_chain import RAGChain
from services.ollama_manager import OllamaManager
from services.raptor_retriever import RaptorRetrieverService

# Определяем, что экспортируется при "from services import *"
__all__ = [
    'DocumentProcessor',
    'SmartChunker', 
    'EmbeddingsManager',
    'VectorStoreManager',
    'HybridRetriever',
    'RAGChain',
    'OllamaManager',
    'RaptorRetrieverService'  # ДОБАВЛЕН
]

# Версия модуля (опционально)
__version__ = '1.0.0'

# Краткое описание модуля
__docformat__ = 'google'
