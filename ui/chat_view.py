"""Chat tab."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import gradio as gr

RespondFn = Callable[[str, list, dict], tuple[str, dict]]
StateFactory = Callable[[], dict]


@dataclass(frozen=True)
class ChatConfig:
    respond: RespondFn
    state_factory: StateFactory
    examples: Sequence[str] = field(default_factory=tuple)
    empty_placeholder: str = "¿En qué puedo ayudarte?"


def build_chat_tab(config: ChatConfig) -> None:
    twin_state = gr.State(config.state_factory())
    examples = [[prompt] for prompt in config.examples] or None

    gr.ChatInterface(
        fn=config.respond,
        chatbot=gr.Chatbot(placeholder=config.empty_placeholder),
        examples=examples,
        additional_inputs=twin_state,
        additional_outputs=twin_state,
        flagging_mode="never",
    )
