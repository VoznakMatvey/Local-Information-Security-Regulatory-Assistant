import streamlit as st
from services.ollama_manager import OllamaManager

def init_session_state():
    """Инициализирует все ключи в st.session_state, если их нет."""
    defaults = {
        "messages": [],
        "vectorstore": None,
        "rag_chain": None,
        "embeddings_manager": None,
        "ollama_manager": None,
        "documents_count": 0,
        "chunks_count": 0,
        "current_chunks": None,
        "raptor": None,
        "raptor_selected_docs": [],
        "raptor_built": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if st.session_state.ollama_manager is None:
        st.session_state.ollama_manager = OllamaManager()

def reset_chat_history():
    st.session_state.messages = []