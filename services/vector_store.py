from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from config import CHROMA_DIR, USE_HYBRID_SEARCH, BM25_WEIGHT, VECTOR_WEIGHT, NEIGHBOUR_CHUNKS
import time
from typing import List
from langchain_core.documents import Document
from collections import defaultdict

class VectorStoreManager:
    def __init__(self, embeddings_manager):
        print("🔧 Инициализация VectorStoreManager...")
        self.embeddings = embeddings_manager.get_embeddings()
        self.vectorstore = None
        self.all_chunks = []  # список всех чанков (документов) для BM25
        print("✅ VectorStoreManager инициализирован")
    
    def _init_vectorstore(self):
        if self.vectorstore is None:
            print("📂 Создание подключения к ChromaDB...")
            self.vectorstore = Chroma(
                persist_directory=str(CHROMA_DIR),
                embedding_function=self.embeddings,
                collection_name="law_documents"
            )
            print("✅ ChromaDB готова")
    
    def add_documents(self, documents):
        print(f"\n📥 Начало индексации: {len(documents)} чанков")
        if not documents:
            print("⚠️ Нет документов для индексации")
            return 0
        
        self.all_chunks = documents
        
        start_total = time.time()
        self._init_vectorstore()
        
        batch_size = 50
        total = len(documents)
        
        for i in range(0, total, batch_size):
            batch_start = time.time()
            batch = documents[i:i+batch_size]
            print(f"\n🔄 Обработка батча {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")
            print(f"   Чанки {i+1} до {min(i+batch_size, total)} из {total}")
            
            try:
                self.vectorstore.add_documents(batch)
                batch_time = time.time() - batch_start
                print(f"   ✅ Батч добавлен за {batch_time:.2f} сек")
            except Exception as e:
                print(f"   ❌ Ошибка при добавлении батча: {e}")
                raise
        
        total_time = time.time() - start_total
        print(f"\n✅ Индексация завершена за {total_time:.2f} секунд")
        print(f"📊 Всего проиндексировано: {total} чанков")
        return total
    
    def search(self, query: str, k: int = 5, use_hybrid: bool = None, expand_context: bool = True):
        if use_hybrid is None:
            use_hybrid = USE_HYBRID_SEARCH
        
        print(f"\n🔍 Поиск: '{query[:50]}...' (k={k}, hybrid={use_hybrid}, expand={expand_context})")
        self._init_vectorstore()
        
        if use_hybrid and len(self.all_chunks) > 0:
            bm25_retriever = BM25Retriever.from_documents(self.all_chunks)
            bm25_retriever.k = k
            vector_retriever = self.vectorstore.as_retriever(search_kwargs={"k": k})
            ensemble = EnsembleRetriever(
                retrievers=[bm25_retriever, vector_retriever],
                weights=[BM25_WEIGHT, VECTOR_WEIGHT]
            )
            start = time.time()
            results = ensemble.get_relevant_documents(query)
            elapsed = time.time() - start
            print(f"✅ Гибридный поиск нашёл {len(results)} результатов за {elapsed:.2f} сек")
        else:
            start = time.time()
            results = self.vectorstore.similarity_search(query, k=k)
            elapsed = time.time() - start
            print(f"✅ Векторный поиск нашёл {len(results)} результатов за {elapsed:.2f} сек")
        
        if expand_context and NEIGHBOUR_CHUNKS > 0:
            expanded = self._expand_with_neighbours(results)
            print(f"📦 Расширение контекста: было {len(results)} чанков, стало {len(expanded)}")
            return expanded
        else:
            return results
    
    def _expand_with_neighbours(self, chunks: List[Document]) -> List[Document]:
        # Группируем все чанки по doc_id
        doc_all_chunks = defaultdict(list)
        for chunk in self.all_chunks:
            doc_id = chunk.metadata.get("doc_id")
            if doc_id:
                doc_all_chunks[doc_id].append(chunk)
        
        doc_map = {}
        for doc_id, chunk_list in doc_all_chunks.items():
            sorted_chunks = sorted(chunk_list, key=lambda x: x.metadata.get("chunk_index", 0))
            index_map = {ch.metadata["chunk_index"]: ch for ch in sorted_chunks}
            max_idx = max(index_map.keys()) if index_map else -1
            doc_map[doc_id] = (index_map, max_idx)
        
        expanded_set = {}
        for chunk in chunks:
            doc_id = chunk.metadata.get("doc_id")
            idx = chunk.metadata.get("chunk_index")
            if doc_id is None or idx is None:
                expanded_set[chunk.metadata.get("chunk_id", id(chunk))] = chunk
                continue
            
            chunk_id = chunk.metadata.get("chunk_id", f"{doc_id}_{idx}")
            expanded_set[chunk_id] = chunk
            
            index_map, max_idx = doc_map.get(doc_id, ({}, -1))
            if not index_map:
                continue
            
            for offset in range(1, NEIGHBOUR_CHUNKS + 1):
                neighbour_idx = idx - offset
                if neighbour_idx >= 0:
                    neighbour = index_map.get(neighbour_idx)
                    if neighbour:
                        expanded_set[neighbour.metadata["chunk_id"]] = neighbour
            for offset in range(1, NEIGHBOUR_CHUNKS + 1):
                neighbour_idx = idx + offset
                if neighbour_idx <= max_idx:
                    neighbour = index_map.get(neighbour_idx)
                    if neighbour:
                        expanded_set[neighbour.metadata["chunk_id"]] = neighbour
        
        return list(expanded_set.values())
    
    def similarity_search(self, query: str, k: int = 5):
        return self.search(query, k=k, use_hybrid=False, expand_context=False)
    
    def delete_collection(self):
        print("🗑️ Удаление коллекции...")
        import shutil
        if self.vectorstore:
            self.vectorstore = None
        if CHROMA_DIR.exists():
            shutil.rmtree(CHROMA_DIR)
            CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            print("✅ Коллекция удалена")
        self.all_chunks = []