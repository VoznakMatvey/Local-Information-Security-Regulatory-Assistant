from typing import List
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP, CHUNK_SEPARATORS
from collections import defaultdict

class SmartChunker:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=CHUNK_SEPARATORS,
            length_function=len,
            keep_separator=True
        )
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Группирует страницы по doc_id, объединяет их в один текст,
        разбивает на чанки и нумерует их сквозным образом.
        """
        # Группируем страницы по doc_id
        pages_by_doc = defaultdict(list)
        for doc in documents:
            doc_id = doc.metadata.get("doc_id")
            if not doc_id:
                # fallback: используем имя файла
                doc_id = doc.metadata.get("filename", str(id(doc)))
            pages_by_doc[doc_id].append(doc)
        
        all_chunks = []
        for doc_id, pages in pages_by_doc.items():
            # Сортируем страницы по номеру
            pages_sorted = sorted(pages, key=lambda x: x.metadata.get("page", 0))
            # Объединяем текст всех страниц
            full_text = "\n".join([page.page_content for page in pages_sorted])
            # Берём метаданные из первой страницы (filename, source, doc_id)
            base_meta = pages_sorted[0].metadata.copy()
            base_meta.pop("page", None)  # убираем номер страницы, он не будет точным
            base_meta["total_pages"] = len(pages_sorted)
            temp_doc = Document(page_content=full_text, metadata=base_meta)
            # Разбиваем на чанки
            chunks = self.text_splitter.split_documents([temp_doc])
            for idx, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = idx
                chunk.metadata["total_chunks"] = len(chunks)
                chunk.metadata["chunk_id"] = f"{doc_id}_{idx}"
                # Убираем лишние метаданные
                chunk.metadata.pop("page", None)
            all_chunks.extend(chunks)
        return all_chunks