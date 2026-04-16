import os
from pathlib import Path
from typing import List
import hashlib
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader, UnstructuredMarkdownLoader
from langchain_core.documents import Document

class DocumentProcessor:
    SUPPORTED_EXTENSIONS = {
        '.pdf': PyPDFLoader,
        '.docx': Docx2txtLoader,
        '.txt': TextLoader,
        '.md': UnstructuredMarkdownLoader
    }
    
    @staticmethod
    def load_documents(folder_path: Path) -> List[Document]:
        documents = []
        for file_path in folder_path.rglob("*"):
            if file_path.suffix.lower() in DocumentProcessor.SUPPORTED_EXTENSIONS:
                try:
                    loader_class = DocumentProcessor.SUPPORTED_EXTENSIONS[file_path.suffix.lower()]
                    loader = loader_class(str(file_path))
                    # Для PDF: loader.load() возвращает список страниц
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["source"] = str(file_path)
                        doc.metadata["filename"] = file_path.name
                        doc.metadata["doc_id"] = hashlib.md5(str(file_path).encode()).hexdigest()
                        # Номер страницы (PyPDFLoader добавляет "page")
                        if "page" not in doc.metadata:
                            doc.metadata["page"] = 1
                        doc.page_content = DocumentProcessor._clean_text(doc.page_content)
                    documents.extend(docs)
                    print(f"✅ Загружен: {file_path.name} ({len(docs)} страниц)")
                except Exception as e:
                    print(f"❌ Ошибка загрузки {file_path.name}: {e}")
        return documents
    
    @staticmethod
    def _clean_text(text: str) -> str:
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.\,\!\?\-\;\:\«\»\(\)\№\—]', '', text)
        return text.strip()
