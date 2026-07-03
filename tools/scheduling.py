from notifications.pushover import push


def check_availability_tool(date: str, time_preference: str = "any"):
    push(f"Consulta de disponibilidad: {date} (preferencia: {time_preference})")
    return (
        f"Disponibilidad simulada para {date}: 10:00, 14:00 y 16:00. "
        "Indicá horario y email para confirmar con schedule_call_tool."
    )


def schedule_call_tool(email: str, date: str, time: str, name: str = "Name not provided"):
    push(f"Call agendada con {name} ({email}) — {date} a las {time}")
    return f"OK — Call confirmada para {date} a las {time}. Seguimiento por {email}."


check_availability_tool_json = {
    "name": "check_availability_tool",
    "description": (
        "Use when the user wants to schedule a call or meeting and needs to know "
        "available time slots on a specific date."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "Date requested (e.g. 2026-07-10)"},
            "time_preference": {
                "type": "string",
                "description": "Preferred time of day: morning, afternoon, evening, or any",
            },
        },
        "required": ["date"],
        "additionalProperties": False,
    },
}

schedule_call_tool_json = {
    "name": "schedule_call_tool",
    "description": (
        "Use when the user confirms they want to book a call and provides email, date, and time."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "The user's email address"},
            "date": {"type": "string", "description": "Confirmed date for the call"},
            "time": {"type": "string", "description": "Confirmed time for the call"},
            "name": {"type": "string", "description": "The user's name, if provided"},
        },
        "required": ["email", "date", "time"],
        "additionalProperties": False,
    },
}
