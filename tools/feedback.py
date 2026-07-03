from notifications.pushover import push


def record_feedback_tool(rating: int, comment: str = ""):
    push(f"Feedback recibido: {rating}/5 - {comment}")
    return "OK"


record_feedback_tool_json = {
    "name": "record_feedback_tool",
    "description": (
        "Use when the user explicitly shares an opinion or rating about the conversation "
        "or the digital twin experience (e.g. 'te doy 5 estrellas', 'muy útil', 'no me gustó')."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "rating": {"type": "integer", "description": "Rating from 1 to 5"},
            "comment": {"type": "string", "description": "Optional comment from the user"},
        },
        "required": ["rating"],
        "additionalProperties": False,
    },
}
