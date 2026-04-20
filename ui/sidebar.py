import streamlit as st
import hashlib
from pathlib import Path
import shutil
import requests

from config import DATA_DIR, CHROMA_DIR, OLLAMA_HOST, OLLAMA_MODEL, TEMPERATURE as DEFAULT_TEMP
from services.document_processor import DocumentProcessor
from services.chunker import SimpleChunker
from services.embeddings_ollama import EmbeddingsManager
from services.vector_store import VectorStoreManager
from services.raptor_retriever import RaptorRetrieverService


def _clean_chunks_for_raptor(chunks):
    """Создаёт копии чанков, удаляя parent_content и обеспечивая уникальность ID."""
    from langchain_core.documents import Document
    cleaned = []
    for ch in chunks:
        meta = ch.metadata.copy()
        # Удаляем поля, которые могут быть слишком длинными для RAPTOR
        meta.pop("parent_content", None)
        # Удаляем chunk_id, чтобы избежать дубликатов ID в RAPTOR
        meta.pop("chunk_id", None)
        # Генерируем новый уникальный ID на основе контента и метаданных
        unique_str = f"{ch.page_content[:100]}_{meta.get('source','')}_{meta.get('page','')}"
        meta["id"] = hashlib.md5(unique_str.encode()).hexdigest()
        cleaned.append(Document(page_content=ch.page_content, metadata=meta))
    return cleaned


def render_sidebar():
    """Отображает боковую панель и возвращает словарь с параметрами, выбранными пользователем."""
    st.sidebar.header("📂 Управление системой")

    # --- Статус LLM ---
    st.sidebar.subheader("🤖 Статус LLM")
    if st.sidebar.button("🔄 Проверить статус Ollama", use_container_width=True):
        with st.sidebar:
            with st.spinner("Проверка..."):
                if st.session_state.ollama_manager.is_running():
                    st.success("✅ Ollama работает")
                    try:
                        resp = requests.get(f"http://{OLLAMA_HOST}/api/tags", timeout=5)
                        models = resp.json().get("models", [])
                        model_names = [m["name"].split(":")[0] for m in models]
                        if OLLAMA_MODEL.split(":")[0] in model_names:
                            st.success(f"✅ Модель {OLLAMA_MODEL} доступна")
                        else:
                            st.warning(f"⚠️ Модель {OLLAMA_MODEL} не загружена")
                    except:
                        st.error("❌ Не удалось проверить модель")
                else:
                    st.error("❌ Ollama не запущен")
                    st.info("Запустите через start.bat или вручную: ollama serve")

    st.sidebar.divider()

    # --- Статистика ---
    st.sidebar.subheader("📊 Статистика базы")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Документов", st.session_state.documents_count)
    with col2:
        st.metric("Чанков", st.session_state.chunks_count)

    if CHROMA_DIR.exists():
        size_bytes = sum(f.stat().st_size for f in CHROMA_DIR.rglob('*') if f.is_file())
        size_mb = size_bytes / (1024 * 1024)
        st.sidebar.caption(f"Размер векторной БД: {size_mb:.1f} МБ")

    st.sidebar.divider()

    # --- Добавить документы ---
    st.sidebar.subheader("📤 Добавить документы")
    uploaded_files = st.sidebar.file_uploader(
        "Загрузите PDF, DOCX или TXT",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="file_uploader"
    )
    if uploaded_files:
        for uploaded_file in uploaded_files:
            save_path = DATA_DIR / uploaded_file.name
            if not save_path.exists():
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.sidebar.success(f"✅ {uploaded_file.name} сохранён")
            else:
                st.sidebar.info(f"ℹ️ {uploaded_file.name} уже существует")

    st.sidebar.divider()

    # --- Индексация ---
    st.sidebar.subheader("🔄 Индексация")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 Переиндексировать всё", type="primary", use_container_width=True):
            with st.spinner("Индексация документов... Это может занять время"):
                try:
                    processor = DocumentProcessor()
                    docs = processor.load_documents(DATA_DIR)
                    st.session_state.documents_count = len(docs)
                    st.info(f"📄 Загружено документов: {len(docs)}")

                    if not docs:
                        st.warning("Нет документов для индексации. Добавьте файлы в папку data/laws/")
                    else:
                        chunker = SimpleChunker()
                        chunks = chunker.split_documents(docs)
                        st.session_state.chunks_count = len(chunks)
                        st.session_state.current_chunks = chunks
                        st.session_state.raptor = None
                        st.session_state.raptor_selected_docs = []
                        st.session_state.raptor_built = False
                        st.info(f"✂️ Создано чанков: {len(chunks)}")

                        if st.session_state.embeddings_manager is None:
                            st.session_state.embeddings_manager = EmbeddingsManager(model_name="bge_m3")

                        vsm = VectorStoreManager(st.session_state.embeddings_manager)
                        vsm.delete_collection()
                        count = vsm.add_documents(chunks)
                        st.session_state.vectorstore = vsm
                        st.success(f"✅ Проиндексировано {count} чанков")
                except Exception as e:
                    st.error(f"❌ Ошибка индексации: {str(e)}")

    with col2:
        if st.button("🗑️ Очистить базу", use_container_width=True):
            try:
                if st.session_state.vectorstore:
                    st.session_state.vectorstore.delete_collection()
                    st.session_state.vectorstore = None
                if st.session_state.raptor:
                    st.session_state.raptor.clear_index()
                    st.session_state.raptor = None
                st.session_state.documents_count = 0
                st.session_state.chunks_count = 0
                st.session_state.current_chunks = None
                st.session_state.raptor_selected_docs = []
                st.session_state.raptor_built = False
                st.success("✅ База очищена")
            except Exception as e:
                st.error(f"❌ Ошибка: {str(e)}")

    st.sidebar.divider()

    # --- RAPTOR ---
    st.sidebar.subheader("🦖 RAPTOR (выборочный)")
    if st.session_state.current_chunks:
        doc_names = sorted(set(chunk.metadata.get("filename") for chunk in st.session_state.current_chunks if chunk.metadata.get("filename")))
        selected_docs = st.sidebar.multiselect(
            "Выберите документы для построения RAPTOR",
            options=doc_names,
            default=st.session_state.raptor_selected_docs,
            key="raptor_doc_selector",
            help="RAPTOR построит дерево только для выбранных документов."
        )
        if st.sidebar.button("🏗️ Построить RAPTOR для выбранных", use_container_width=True, key="build_raptor_btn"):
            if not selected_docs:
                st.warning("Выберите хотя бы один документ")
            else:
                raptor_chunks = [ch for ch in st.session_state.current_chunks if ch.metadata.get("filename") in selected_docs]
                if len(raptor_chunks) < 5:
                    st.warning(f"Выбрано слишком мало фрагментов ({len(raptor_chunks)}). RAPTOR может быть неэффективен.")
                else:
                    doc_key = hashlib.md5("".join(sorted(selected_docs)).encode()).hexdigest()[:8]
                    collection_name = f"raptor_{doc_key}"
                    with st.spinner(f"🦖 Построение RAPTOR для {len(raptor_chunks)} фрагментов..."):
                        raptor = RaptorRetrieverService(
                            embedding_model_name="bge-m3:latest",
                            collection_name=collection_name
                        )
                        # Очищаем чанки перед передачей в RAPTOR
                        cleaned_chunks = _clean_chunks_for_raptor(raptor_chunks)
                        raptor.build_index(cleaned_chunks)
                        st.session_state.raptor = raptor
                        st.session_state.raptor_selected_docs = selected_docs
                        st.session_state.raptor_built = True
                    st.success(f"RAPTOR готов для {len(selected_docs)} документов")

        if st.session_state.raptor_built:
            st.sidebar.info(f"✅ Активный RAPTOR для: {', '.join(st.session_state.raptor_selected_docs)}")
        else:
            st.sidebar.info("RAPTOR не построен.")
    else:
        st.sidebar.info("Сначала переиндексируйте документы")

    st.sidebar.divider()

    # --- Настройки поиска ---
    st.sidebar.subheader("⚙️ Настройки поиска")
    temperature = st.sidebar.slider(
        "Креативность ответов",
        min_value=0.0,
        max_value=1.0,
        value=DEFAULT_TEMP,
        step=0.1,
        help="Меньше = точнее и строже, больше = креативнее"
    )
    top_k = st.sidebar.slider(
        "Количество чанков для поиска",
        min_value=1,
        max_value=20,
        value=10,
        help="Больше = точнее, но медленнее"
    )
    use_hybrid = st.sidebar.checkbox("Гибридный поиск (BM25 + векторный)", value=True, key="use_hybrid")
    use_reasoning = st.sidebar.checkbox("Режим размышления (reasoning)", value=False, key="use_reasoning")

    use_raptor = False
    if st.session_state.raptor_built:
        use_raptor = st.sidebar.checkbox("Использовать RAPTOR для ответа", value=False, key="use_raptor_checkbox")
    else:
        st.sidebar.caption("ℹ️ RAPTOR недоступен – сначала построите его")

    st.sidebar.divider()

    st.sidebar.caption("📌 **О системе**")
    st.sidebar.caption("• Все данные хранятся локально")
    st.sidebar.caption(f"• Модель: {OLLAMA_MODEL}")
    st.sidebar.caption("• Простой чанкинг + ParentDocumentRetriever")
    st.sidebar.caption("• Гибридный поиск")
    st.sidebar.caption("• RAPTOR (выборочный)")

    if st.sidebar.button("🗑️ Очистить историю чата", use_container_width=True):
        st.session_state.messages = []

    return {
        "temperature": temperature,
        "top_k": top_k,
        "use_hybrid": use_hybrid,
        "use_reasoning": use_reasoning,
        "use_raptor": use_raptor,
    }