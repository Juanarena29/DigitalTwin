from tools.session_state import get_session_state


def get_checklist_report() -> str:
    state = get_session_state()
    checklist = state["checklist"]
    completed = state["completed"]
    if not checklist:
        return "No checklist items yet."

    lines = []
    for index, item in enumerate(checklist):
        status = "done" if completed[index] else "pending"
        prefix = "[x]" if status == "done" else "[ ]"
        lines.append(f"Checklist #{index + 1}: {prefix} {item}")
    report = "\n".join(lines)
    print(f"[Checklist]\n{report}", flush=True)
    return report


def create_checklist(descriptions: list[str]) -> str:
    state = get_session_state()
    state["checklist"].extend(descriptions)
    state["completed"].extend([False] * len(descriptions))
    return get_checklist_report()


def mark_complete(index: int, completion_notes: str) -> str:
    state = get_session_state()
    checklist = state["checklist"]
    if 1 <= index <= len(checklist):
        state["completed"][index - 1] = True
        print(f"[Checklist] Item {index}: {completion_notes}", flush=True)
        return get_checklist_report()
    return "No checklist at this index."


create_checklist_json = {
    "name": "create_checklist",
    "description": (
        "Use ONLY for complex multi-step questions about career or experience "
        "(e.g. compare two roles, explain impact across projects). "
        "Creates a visible plan before answering. "
        "Do NOT use for simple factual questions like 'what do you do?' or 'what skills do you have?'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "descriptions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Step descriptions for the plan",
            }
        },
        "required": ["descriptions"],
        "additionalProperties": False,
    },
}

mark_complete_json = {
    "name": "mark_complete",
    "description": (
        "Mark a checklist item complete (1-based index) after finishing that step. "
        "Use together with create_checklist on complex questions only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "index": {
                "type": "integer",
                "description": "The 1-based index of the checklist item to mark complete",
            },
            "completion_notes": {
                "type": "string",
                "description": "Brief note on how the step was completed",
            },
        },
        "required": ["index", "completion_notes"],
        "additionalProperties": False,
    },
}
