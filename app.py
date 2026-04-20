"""
Локальная ВОС для НПА в сфере информационной безопасности
Главный файл интерфейса Streamlit
"""

import streamlit as st

from ui.styles import apply_custom_styles
from session.state import init_session_state
from ui.sidebar import render_sidebar
from ui.chat import render_chat

st.set_page_config(
    page_title="НПА ИБ Помощник",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_styles()
init_session_state()

st.markdown('<div class="main-header">⚖️ Локальный помощник по НПА в сфере ИБ</div>', unsafe_allow_html=True)
st.caption("Полностью локальная система | Работает офлайн | Ваши данные никуда не передаются")

# Рендерим боковую панель и получаем параметры
params = render_sidebar()

# Основная область чата
render_chat(params)

st.divider()
st.caption("💡 **Совет:** Для лучших результатов загрузите в систему актуальные версии законов, приказов и нормативно-правовых актов в сфере ИБ.")