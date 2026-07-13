"""Top-level layout composition."""

from dataclasses import dataclass

import gradio as gr

from ui.analytics_view import AnalyticsPorts, build_analytics_tab
from ui.chat_view import ChatConfig, build_chat_tab


@dataclass(frozen=True)
class AppLayout:
    page_title: str
    header_title: str
    header_subtitle: str
    chat: ChatConfig
    analytics: AnalyticsPorts


def build_app(layout: AppLayout) -> gr.Blocks:
    with gr.Blocks(title=layout.page_title) as demo:
        gr.Markdown(f"# {layout.header_title}\n{layout.header_subtitle}")

        with gr.Tabs():
            with gr.Tab("Chat"):
                build_chat_tab(layout.chat)
            with gr.Tab("Analytics"):
                build_analytics_tab(layout.analytics)

    return demo


def launch_app(layout: AppLayout, **launch_kwargs) -> None:
    build_app(layout).launch(**launch_kwargs)
