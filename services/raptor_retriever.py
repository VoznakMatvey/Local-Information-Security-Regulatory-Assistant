import logging
import nest_asyncio
from typing import List, Any
from llama_index.core import Document as LlamaDocument
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.packs.raptor import RaptorPack
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from config import OLLAMA_HOST, OLLAMA_MODEL, CHROMA_DIR

nest_asyncio.apply()

logger = logging.getLogger(__name__)

class RaptorRetrieverService:
    def __init__(self, embedding_model_name: str = "bge-m3:latest", collection_name: str = "raptor_law_documents"):
        self.embedding_model_name = embedding_model_name
        self._raptor_pack = None
        self._is_built = False
        self._vector_store = None
        self._chroma_client = None
        self._collection_name = collection_name

        self.llm = Ollama(
            model=OLLAMA_MODEL,
            request_timeout=120.0,
            base_url=f"http://{OLLAMA_HOST}"
        )
        self.embed_model = OllamaEmbedding(
            model_name=self.embedding_model_name,
            base_url=f"http://{OLLAMA_HOST}"
        )

    def _get_vector_store(self):
        if self._vector_store is None:
            self._chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            # Принудительно удаляем и создаём коллекцию, чтобы быть уверенными
            try:
                self._chroma_client.delete_collection(self._collection_name)
                print(f"Старая коллекция {self._collection_name} удалена")
            except Exception as e:
                print(f"Коллекция не существовала или не удалилась: {e}")
            try:
                collection = self._chroma_client.create_collection(self._collection_name)
                print(f"Коллекция {self._collection_name} создана")
            except Exception as e:
                # Если уже существует (гонка), просто получаем
                collection = self._chroma_client.get_collection(self._collection_name)
                print(f"Коллекция {self._collection_name} получена")
            self._vector_store = ChromaVectorStore(chroma_collection=collection)
        return self._vector_store

    def build_index(self, documents: List[Any]) -> bool:
        if not documents:
            return False

        # Принудительно пересоздаём векторное хранилище (и коллекцию)
        self._vector_store = None
        vector_store = self._get_vector_store()
        
        print(f"Построение RAPTOR индекса для {len(documents)} фрагментов...")
        llama_docs = [LlamaDocument(text=doc.page_content, metadata=doc.metadata) for doc in documents]
        self._raptor_pack = RaptorPack(
            documents=llama_docs,
            llm=self.llm,
            embed_model=self.embed_model,
            vector_store=vector_store,
            similarity_top_k=5,
        )
        self._raptor_pack.run("initialize")
        self._is_built = True
        print("RAPTOR индекс построен и сохранён")
        return True

    def retrieve(self, query: str, mode: str = "collapsed", top_k: int = 5) -> List[Any]:
        if not self._is_built:
            print("RAPTOR индекс не загружен, сначала вызовите build_index()")
            return []
        nodes = self._raptor_pack.run(query, mode=mode)
        from langchain_core.documents import Document
        return [Document(page_content=node.text, metadata=node.metadata) for node in nodes[:top_k]]

    def clear_index(self):
        if self._chroma_client:
            try:
                self._chroma_client.delete_collection(self._collection_name)
            except Exception as e:
                print(f"Ошибка удаления: {e}")
            self._vector_store = None
            self._raptor_pack = None
            self._is_built = False