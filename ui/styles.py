import streamlit as st

def apply_custom_styles():
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