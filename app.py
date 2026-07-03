from dotenv import load_dotenv
import streamlit as st

from agent.loop import chat
from config import TWIN_NAME
from dashboard.analytics import render_analytics
from memory.db import init_db
from styles import CSS, EXAMPLES

load_dotenv(override=True)
init_db()


def _default_twin_state() -> dict:
    return {"session_id": None, "checklist": [], "completed": []}


def _init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "twin_state" not in st.session_state:
        st.session_state.twin_state = _default_twin_state()


def _render_chat() -> None:
    st.markdown(
        '<p class="twin-subtitle">Una conversación simple sobre mi perfil, experiencia y proyectos.</p>',
        unsafe_allow_html=True,
    )

    messages_container = st.container()

    prompt = st.session_state.pop("pending_prompt", None)
    if prompt is None:
        prompt = st.chat_input("Escribí tu mensaje...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

    with messages_container:
        if not st.session_state.messages:
            st.markdown(
                """
                <div class="twin-empty-state">
                  <div class="twin-empty-icon">&#9670;</div>
                  <p class="twin-empty-title">¿En qué puedo ayudarte?</p>
                  <p class="twin-empty-sub">Preguntame sobre mi experiencia, proyectos o cómo contactarme.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            cols = st.columns(2)
            for index, example in enumerate(EXAMPLES):
                with cols[index % 2]:
                    st.markdown('<div class="example-btn">', unsafe_allow_html=True)
                    if st.button(example, key=f"example_{index}", use_container_width=True):
                        st.session_state.pending_prompt = example
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            last_prompt = st.session_state.messages[-1]["content"]
            history = st.session_state.messages[:-1]
            with st.chat_message("assistant"):
                placeholder = st.empty()
                placeholder.markdown(
                    '<div class="typing-dots"><span></span><span></span><span></span></div>',
                    unsafe_allow_html=True,
                )
                response, twin_state = chat(
                    last_prompt, history, st.session_state.twin_state
                )
                st.session_state.twin_state = twin_state
                placeholder.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title=f"Digital Twin — {TWIN_NAME}",
        page_icon=".",
        layout="centered",
    )
    st.markdown(CSS, unsafe_allow_html=True)
    _init_session()

    st.markdown(f'<h1 class="twin-title">{TWIN_NAME}</h1>', unsafe_allow_html=True)

    chat_tab, analytics_tab = st.tabs(["Chat", "Analytics"])
    with chat_tab:
        _render_chat()
    with analytics_tab:
        render_analytics()


if __name__ == "__main__":
    main()
