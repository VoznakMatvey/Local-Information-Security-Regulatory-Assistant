from typing import List, Tuple
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from config import RETRIEVAL_TOP_K

class HybridRetriever:
    """
    Комбинирует семантический поиск (Chroma) и ключевой (BM25).
    BM25 отлично работает для точных цитат и юридических терминов.
    """
    
    def __init__(self, vectorstore, chunks_list: List):
        self.vector_retriever = vectorstore.as_retriever(
            search_kwargs={"k": RETRIEVAL_TOP_K}
        )
        
        # BM25 требует список текстов
        texts = [chunk.page_content for chunk in chunks_list]
        self.bm25_retriever = BM25Retriever.from_texts(texts)
        self.bm25_retriever.k = RETRIEVAL_TOP_K
        
        # Создаём ансамбль с весами (0.5 векторный, 0.5 ключевой)
        self.ensemble = EnsembleRetriever(
            retrievers=[self.vector_retriever, self.bm25_retriever],
            weights=[0.5, 0.5]
        )
    
    def get_relevant_documents(self, query: str) -> List[Tuple]:
        """Возвращает релевантные чанки с оценками"""
        return self.ensemble.get_relevant_documents(query)
