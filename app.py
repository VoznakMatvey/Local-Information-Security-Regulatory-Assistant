"""
Локальная ВОС для НПА в сфере информационной безопасности
Главный файл интерфейса Streamlit
"""

import streamlit as st
import shutil
from pathlib import Path
import hashlib

# Импорт наших сервисов
from config import DATA_DIR, CHROMA_DIR, OLLAMA_MODEL
from services.document_processor import DocumentProcessor
from services.chunker import SmartChunker
from services.embeddings_ollama import EmbeddingsManager
from services.vector_store import VectorStoreManager
from services.rag_chain import RAGChain
from services.ollama_manager import OllamaManager
from services.raptor_retriever import RaptorRetrieverService

# Настройка страницы
st.set_page_config(
    page_title="НПА ИБ Помощник",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Кастомный CSS (без изменений, для краткости оставлен как в исходнике)
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #1f77b4; text-align: center; margin-bottom: 1rem; }
    .stChatMessage { background-color: #f0f2f6; border-radius: 10px; padding: 10px; }
    .source-info { font-size: 0.8rem; color: #666; margin-top: 5px; }
    @media (prefers-color-scheme: dark) {
        .stChatMessage { background-color: #2d2d2d !important; }
        .stChatMessage .stMarkdown, .stChatMessage .stMarkdown p, .stChatMessage .stMarkdown div,
        .stChatMessage [data-testid="stChatMessageContent"] { color: #ffffff !important; }
        .stChatMessage [data-testid="stChatMessageContent"] p { color: #ffffff !important; }
        h1, h2, h3, h4, h5, h6, .stHeading, .stHeader { color: #ffffff !important; }
        .streamlit-expanderHeader, .streamlit-expanderContent, .streamlit-expanderContent p,
        .streamlit-expanderContent div { color: #ffffff !important; background-color: #1e1e1e !important; }
        .stCaption, caption, .stCaption p { color: #aaaaaa !important; }
        .stMetric label, .stMetric .stMetricValue, .stMetric .stMetricDelta { color: #ffffff !important; }
        .sidebar .sidebar-content, .sidebar .stMarkdown, .sidebar .stMarkdown p { color: #ffffff !important; }
        .stSlider label, .stSelectbox label, .stNumberInput label, .stRadio label { color: #ffffff !important; }
        .stSlider .stMarkdown { color: #ffffff !important; }
        .stCaption, .stMarkdown small { color: #aaaaaa !important; }
        .stAlert p, .stInfo p, .stSuccess p, .stWarning p, .stError p { color: #000000 !important; }
        .stButton button { color: #ffffff !important; }
        .stFileUploader label { color: #ffffff !important; }
        div, p, span, label { color: inherit; }
    }
</style>
""", unsafe_allow_html=True)

# Инициализация сессионных переменных
if "messages" not in st.session_state:
    st.session_state.messages = []
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "rag_chain" not in st.session_state:
    st.session_state.rag_chain = None
if "embeddings_manager" not in st.session_state:
    st.session_state.embeddings_manager = None
if "ollama_manager" not in st.session_state:
    st.session_state.ollama_manager = None
if "documents_count" not in st.session_state:
    st.session_state.documents_count = 0
if "chunks_count" not in st.session_state:
    st.session_state.chunks_count = 0
if "current_chunks" not in st.session_state:
    st.session_state.current_chunks = None
if "raptor" not in st.session_state:
    st.session_state.raptor = None
if "raptor_selected_docs" not in st.session_state:
    st.session_state.raptor_selected_docs = []
if "raptor_built" not in st.session_state:
    st.session_state.raptor_built = False

# Заголовок
st.markdown('<div class="main-header">⚖️ Локальный помощник по НПА в сфере ИБ</div>', unsafe_allow_html=True)
st.caption("Полностью локальная система | Работает офлайн | Ваши данные никуда не передаются")

# Боковая панель
with st.sidebar:
    st.header("📂 Управление системой")
    
    # Статус Ollama
    st.subheader("🤖 Статус LLM")
    if st.session_state.ollama_manager is None:
        st.session_state.ollama_manager = OllamaManager()
    
    if st.button("🔄 Проверить статус Ollama", use_container_width=True):
        with st.spinner("Проверка..."):
            if st.session_state.ollama_manager.is_running():
                st.success("✅ Ollama работает")
                try:
                    import requests
                    from config import OLLAMA_HOST
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
    
    st.divider()
    
    # Статистика базы знаний
    st.subheader("📊 Статистика базы")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Документов", st.session_state.documents_count)
    with col2:
        st.metric("Чанков", st.session_state.chunks_count)
    
    if CHROMA_DIR.exists():
        size_bytes = sum(f.stat().st_size for f in CHROMA_DIR.rglob('*') if f.is_file())
        size_mb = size_bytes / (1024 * 1024)
        st.caption(f"Размер векторной БД: {size_mb:.1f} МБ")
    
    st.divider()
    
    # Загрузка новых документов
    st.subheader("📤 Добавить документы")
    uploaded_files = st.file_uploader(
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
                st.success(f"✅ {uploaded_file.name} сохранён")
            else:
                st.info(f"ℹ️ {uploaded_file.name} уже существует")
    
    st.divider()
    
    # Управление индексацией
    st.subheader("🔄 Индексация")
    
    col1, col2 = st.columns(2)
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
                        chunker = SmartChunker()
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
    
    st.divider()
    
    # ==================== ВЫБОРОЧНЫЙ RAPTOR ====================
   # ==================== ВЫБОРОЧНЫЙ RAPTOR ====================
    st.subheader("🦖 RAPTOR (выборочный)")
    if st.session_state.current_chunks:
        # Получаем уникальные имена документов
        doc_names = sorted(set(chunk.metadata.get("filename") for chunk in st.session_state.current_chunks if chunk.metadata.get("filename")))
        selected_docs = st.multiselect(
            "Выберите документы для построения RAPTOR",
            options=doc_names,
            default=st.session_state.raptor_selected_docs,
            key="raptor_doc_selector",   # уникальный ключ
            help="RAPTOR построит дерево только для выбранных документов. Это быстрее."
        )
        
        if st.button("🏗️ Построить RAPTOR для выбранных", use_container_width=True, key="build_raptor_btn"):
            if not selected_docs:
                st.warning("Выберите хотя бы один документ")
            else:
                # Фильтруем чанки
                raptor_chunks = [ch for ch in st.session_state.current_chunks if ch.metadata.get("filename") in selected_docs]
                if len(raptor_chunks) < 5:
                    st.warning(f"Выбрано слишком мало фрагментов ({len(raptor_chunks)}). RAPTOR может быть неэффективен.")
                else:
                    # Генерируем уникальное имя коллекции
                    import hashlib
                    doc_key = hashlib.md5("".join(sorted(selected_docs)).encode()).hexdigest()[:8]
                    collection_name = f"raptor_{doc_key}"
                    with st.spinner(f"🦖 Построение RAPTOR для {len(raptor_chunks)} фрагментов (может занять время)..."):
                        raptor = RaptorRetrieverService(
                            embedding_model_name="bge-m3:latest",
                            collection_name=collection_name
                        )
                        raptor.build_index(raptor_chunks)
                        st.session_state.raptor = raptor
                        st.session_state.raptor_selected_docs = selected_docs
                        st.session_state.raptor_built = True
                    st.success(f"RAPTOR готов для {len(selected_docs)} документов")
                    # Принудительно перезапускаем, чтобы обновить чекбокс и информацию
                    st.rerun()
        
        # Отображаем текущий активный RAPTOR
        if st.session_state.raptor_built:
            st.info(f"✅ Активный RAPTOR для: {', '.join(st.session_state.raptor_selected_docs)}")
        else:
            st.info("RAPTOR не построен. Выберите документы и нажмите кнопку выше.")
    else:
        st.info("Сначала переиндексируйте документы")
    
    st.divider()
    # ============================================================
    
    # Настройки поиска
    st.subheader("⚙️ Настройки поиска")
    
    temperature = st.slider(
        "Креативность ответов",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="Меньше = точнее и строже, больше = креативнее"
    )
    
    top_k = st.slider(
        "Количество чанков для поиска",
        min_value=1,
        max_value=20,
        value=10,
        help="Больше = точнее, но медленнее"
    )
    
    use_hybrid = st.checkbox(
        "Гибридный поиск (BM25 + векторный)",
        value=True,
        help="Комбинирует поиск по смыслу и по ключевым словам"
    )
    
    expand_context = st.checkbox(
        "Расширять контекст соседними чанками",
        value=True,
        help="Добавляет соседние чанки из того же документа"
    )
    
    # Чекбокс для использования RAPTOR (только если он построен)
    if st.session_state.raptor_built:
        use_raptor = st.checkbox(
            "Использовать RAPTOR для ответа",
            value=False,
            key="use_raptor_checkbox",
            help="Ответ будет генерироваться на основе иерархического дерева"
        )
    else:
        use_raptor = False
        st.caption("ℹ️ RAPTOR недоступен – сначала построите его для выбранных документов")
    
    if temperature != 0.3:
        import config
        config.TEMPERATURE = temperature
    
    st.divider()
    
    # Информация
    st.caption("📌 **О системе**")
    st.caption("• Все данные хранятся локально")
    st.caption(f"• Модель: {OLLAMA_MODEL}")
    st.caption("• Фиксированный чанкинг (2048 символов)")
    st.caption("• Гибридный поиск + расширение контекста")
    st.caption("• RAPTOR (выборочный)")
    st.caption("• Поддерживает PDF, DOCX, TXT")
    
    if st.button("🗑️ Очистить историю чата", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Основная область — чат
st.header("💬 Задайте вопрос по НПА ИБ")

# Отображение истории сообщений
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("📚 Источники"):
                for src in message["sources"]:
                    st.caption(f"📄 {src}")

# Поле ввода
if prompt := st.chat_input("Введите ваш вопрос о законах, приказах или НПА в сфере ИБ..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Проверка готовности
    if st.session_state.vectorstore is None and not use_raptor:
        with st.chat_message("assistant"):
            st.warning("⚠️ База знаний не проиндексирована. Добавьте документы и нажмите 'Переиндексировать всё'.")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "База знаний не проиндексирована. Пожалуйста, добавьте документы в папку `data/laws/` и нажмите кнопку 'Переиндексировать всё' в боковой панели."
            })
        st.stop()
    
    if use_raptor and not st.session_state.raptor_built:
        with st.chat_message("assistant"):
            st.warning("⚠️ RAPTOR не построен. Выберите документы и нажмите 'Построить RAPTOR для выбранных'.")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Для использования RAPTOR необходимо сначала выбрать документы и построить дерево."
            })
        st.stop()
    
    if st.session_state.ollama_manager is None:
        st.session_state.ollama_manager = OllamaManager()
    
    if not st.session_state.ollama_manager.is_running():
        with st.chat_message("assistant"):
            st.error("❌ Ollama не запущен. Запустите сервер через start.bat")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Ошибка: Ollama сервер не запущен. Пожалуйста, запустите систему через start.bat"
            })
        st.stop()
    
    with st.chat_message("assistant"):
        with st.spinner("🔍 Поиск в нормативно-правовых актах..."):
            try:
                if use_raptor:
                    # Используем уже построенный RAPTOR
                    relevant_docs = st.session_state.raptor.retrieve(prompt, mode="collapsed", top_k=top_k)
                else:
                    # Обычный гибридный поиск
                    relevant_docs = st.session_state.vectorstore.search(
                        query=prompt,
                        k=top_k,
                        use_hybrid=use_hybrid,
                        expand_context=expand_context
                    )
                
                if not relevant_docs:
                    st.info("ℹ️ Не найдено релевантных документов. Попробуйте изменить вопрос или добавьте больше НПА.")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Не найдено релевантных документов. Попробуйте изменить вопрос или добавьте больше НПА в базу знаний."
                    })
                    st.stop()
                
                with st.expander("🔍 Найденные фрагменты в документах"):
                    for i, doc in enumerate(relevant_docs[:5]):
                        source = Path(doc.metadata.get("source", "Неизвестно")).name
                        chunk_idx = doc.metadata.get("chunk_index", "?")
                        st.caption(f"**Фрагмент {i+1}:** {source}, чанк {chunk_idx}")
                        st.text(doc.page_content[:500] + "...")
                        st.divider()
                
                if st.session_state.rag_chain is None:
                    st.session_state.rag_chain = RAGChain()
                
                with st.spinner("🤖 Генерация ответа с помощью LLM..."):
                    result = st.session_state.rag_chain.ask(prompt, relevant_docs, temperature=temperature)
                    
                    if result["success"]:
                        st.markdown(result["answer"])
                        
                        sources = []
                        for doc in result["context_docs"]:
                            source = doc.metadata.get("source", "Неизвестно")
                            filename = Path(source).name
                            chunk_idx = doc.metadata.get("chunk_index", "")
                            chunk_str = f", чанк {chunk_idx}" if chunk_idx != "" else ""
                            sources.append(f"{filename}{chunk_str}")
                        
                        unique_sources = list(dict.fromkeys(sources))
                        
                        with st.expander("📚 Использованные источники"):
                            for src in unique_sources:
                                st.caption(f"📄 {src}")
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result["answer"],
                            "sources": unique_sources
                        })
                    else:
                        st.error(result["answer"])
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Ошибка: {result['answer']}"
                        })
                        
            except Exception as e:
                st.error(f"❌ Произошла ошибка: {str(e)}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Произошла ошибка при обработке запроса: {str(e)}"
                })

st.divider()
st.caption("💡 **Совет:** Для лучших результатов загрузите в систему актуальные версии законов, приказов и нормативно-правовых актов в сфере ИБ.")
