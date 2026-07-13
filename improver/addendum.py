"""Behavior addendum — learned instructions appended to the system prompt."""

from config import BEHAVIOR_ADDENDUM_PATH


def load_behavior_addendum() -> str:
    if not BEHAVIOR_ADDENDUM_PATH.exists():
        return ""
    return BEHAVIOR_ADDENDUM_PATH.read_text(encoding="utf-8").strip()


def save_behavior_addendum(text: str) -> None:
    BEHAVIOR_ADDENDUM_PATH.parent.mkdir(parents=True, exist_ok=True)
    BEHAVIOR_ADDENDUM_PATH.write_text(text.strip(), encoding="utf-8")
