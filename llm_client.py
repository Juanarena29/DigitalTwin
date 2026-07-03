from openai import OpenAI

from config import MODEL_NAME

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def chat_completion(messages, tools=None, model=None, response_format=None):
    kwargs = {"model": model or MODEL_NAME, "messages": messages}
    if tools is not None:
        kwargs["tools"] = tools
    if response_format is not None:
        kwargs["response_format"] = response_format
    return get_client().chat.completions.create(**kwargs)
