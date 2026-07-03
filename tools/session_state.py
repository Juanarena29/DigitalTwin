from contextvars import ContextVar

_session_state: ContextVar[dict | None] = ContextVar("session_state", default=None)


def bind_session_state(state: dict) -> None:
    _session_state.set(state)


def get_session_state() -> dict:
    state = _session_state.get()
    if state is None:
        state = {"checklist": [], "completed": []}
        _session_state.set(state)
    return state
