"""Composition root — wires business logic to the Gradio UI."""

from dotenv import load_dotenv
import gradio as gr

from agent.loop import chat
from config import DASHBOARD_PASSWORD, TWIN_NAME
from dashboard import clear_metrics_cache, dashboard_password_configured, load_metrics
from improver import count_max_retry_failures, get_behavior_addendum, regenerate_behavior_addendum
from memory.db import init_db
from styles import EXAMPLES
from ui.analytics_view import AnalyticsPorts
from ui.chat_view import ChatConfig
from ui.layout import AppLayout, build_app as build_layout, launch_app

load_dotenv(override=True)
init_db()

_HEADER_SUBTITLE = "Una conversación simple sobre mi perfil, experiencia y proyectos."
_CHAT_EMPTY_PLACEHOLDER = (
    "¿En qué puedo ayudarte? Preguntame sobre mi experiencia, proyectos o cómo contactarme."
)
_DASHBOARD_LOCKED_MESSAGE = (
    "Configurá `DASHBOARD_PASSWORD` en tu `.env` para acceder al dashboard."
)


def _default_twin_state() -> dict:
    return {"session_id": None, "checklist": [], "completed": []}


def _respond(message: str, history: list, twin_state: dict) -> tuple[str, dict]:
    return chat(message, list(history), twin_state)


def _authenticate(password: str) -> bool:
    return dashboard_password_configured() and password == DASHBOARD_PASSWORD


def _chat_config() -> ChatConfig:
    return ChatConfig(
        respond=_respond,
        state_factory=_default_twin_state,
        examples=EXAMPLES,
        empty_placeholder=_CHAT_EMPTY_PLACEHOLDER,
    )


def _analytics_ports() -> AnalyticsPorts:
    return AnalyticsPorts(
        is_configured=dashboard_password_configured,
        authenticate=_authenticate,
        load_data=load_metrics,
        clear_cache=clear_metrics_cache,
        not_configured_message=_DASHBOARD_LOCKED_MESSAGE,
        count_behavior_failures=count_max_retry_failures,
        get_behavior_addendum=get_behavior_addendum,
        regenerate_behavior=regenerate_behavior_addendum,
    )


def _app_layout() -> AppLayout:
    return AppLayout(
        page_title=f"Digital Twin - {TWIN_NAME}",
        header_title=f"Digital Twin - {TWIN_NAME}",
        header_subtitle=_HEADER_SUBTITLE,
        chat=_chat_config(),
        analytics=_analytics_ports(),
    )


def build_app() -> gr.Blocks:
    return build_layout(_app_layout())


def main() -> None:
    launch_app(_app_layout())


if __name__ == "__main__":
    main()
