import streamlit as st
from pathlib import Path
from services.rag_chain import RAGChain

def render_chat(params):
    """Отображает историю чата, поле ввода и обрабатывает новые сообщения."""
    st.header("💬 Задайте вопрос по НПА ИБ")

    # Отображение истории сообщений
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sources" in message and message["sources"]:
                with st.expander("📚 Источники"):
                    for src in message["sources"]:
                        st.caption(f"📄 {src}")

    prompt = st.chat_input("Введите ваш вопрос о законах, приказах или НПА в сфере ИБ...")
    if not prompt:
        return

    # Добавляем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Проверки перед поиском
    if not params["use_raptor"] and st.session_state.vectorstore is None:
        with st.chat_message("assistant"):
            st.warning("⚠️ База знаний не проиндексирована. Добавьте документы и нажмите 'Переиндексировать всё'.")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "База знаний не проиндексирована. Пожалуйста, добавьте документы и выполните индексацию."
            })
        return

    if params["use_raptor"] and not st.session_state.raptor_built:
        with st.chat_message("assistant"):
            st.warning("⚠️ RAPTOR не построен. Выберите документы и нажмите 'Построить RAPTOR'.")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Для использования RAPTOR необходимо сначала выбрать документы и построить дерево."
            })
        return

    if not st.session_state.ollama_manager.is_running():
        with st.chat_message("assistant"):
            st.error("❌ Ollama не запущен. Запустите сервер через start.bat")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Ошибка: Ollama сервер не запущен."
            })
        return

    # Выполняем поиск и генерацию
    with st.chat_message("assistant"):
        with st.spinner("🔍 Поиск в нормативно-правовых актах..."):
            try:
                if params["use_raptor"]:
                    relevant_docs = st.session_state.raptor.retrieve(prompt, mode="collapsed", top_k=params["top_k"])
                else:
                    relevant_docs = st.session_state.vectorstore.search(
                        query=prompt,
                        k=params["top_k"],
                        use_hybrid=params["use_hybrid"]
                        # expand_context больше не используется
                    )

                if not relevant_docs:
                    st.info("ℹ️ Не найдено релевантных документов. Попробуйте изменить вопрос.")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Не найдено релевантных документов. Попробуйте изменить вопрос или добавьте больше НПА."
                    })
                    return

                # Показываем найденные фрагменты (первые 5)
                with st.expander("🔍 Найденные фрагменты в документах"):
                    for i, doc in enumerate(relevant_docs[:5]):
                        source = Path(doc.metadata.get("source", "Неизвестно")).name
                        article = doc.metadata.get("article", "")
                        header = doc.metadata.get("header_1", "")
                        info = f"**Фрагмент {i+1}:** {source}"
                        if article:
                            info += f", {article}"
                        elif header:
                            info += f", {header}"
                        st.caption(info)
                        st.text(doc.page_content[:500] + "...")
                        st.divider()

                if st.session_state.rag_chain is None:
                    st.session_state.rag_chain = RAGChain()

                with st.spinner("🤖 Генерация ответа с помощью LLM..."):
                    result = st.session_state.rag_chain.ask(
                        prompt,
                        relevant_docs,
                        temperature=params["temperature"],
                        reasoning=params["use_reasoning"]
                    )

                if result["success"]:
                    st.markdown(result["answer"])

                    sources = []
                    for doc in result["context_docs"]:
                        source = doc.metadata.get("source", "Неизвестно")
                        filename = Path(source).name
                        article = doc.metadata.get("article", "")
                        if article:
                            sources.append(f"{filename} ({article})")
                        else:
                            sources.append(filename)

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
                    "content": f"Произошла ошибка: {str(e)}"
                })