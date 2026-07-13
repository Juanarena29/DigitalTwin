import json
from datetime import datetime, timezone

from memory.db import get_connection


def insert_message(session_id: str, role: str, content: str, timestamp: str | None = None) -> None:
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (session_id, timestamp, role, content) VALUES (?, ?, ?, ?)",
            (session_id, ts, role, content),
        )
        conn.commit()


def save_turn(
    session_id: str,
    user_message: str,
    assistant_response: str,
    tools_used: list[str] | None = None,
    evaluator_attempts: int = 0,
    evaluator_passed: bool = True,
    evaluator_detail: dict | None = None,
) -> None:
    try:
        ts = datetime.now(timezone.utc).isoformat()
        insert_message(session_id, "user", user_message, ts)
        insert_message(session_id, "assistant", assistant_response, ts)
        if tools_used:
            insert_message(session_id, "tool_log", json.dumps(tools_used), ts)
        if evaluator_detail is not None:
            insert_message(session_id, "evaluator_log", json.dumps(evaluator_detail), ts)
        elif evaluator_attempts > 0:
            insert_message(
                session_id,
                "evaluator_log",
                json.dumps({"attempts": evaluator_attempts, "passed": evaluator_passed}),
                ts,
            )
    except Exception as exc:
        print(f"[Memory] Failed to save turn: {exc}", flush=True)


def fetch_max_retry_failures() -> list[dict]:
    from config import MAX_EVAL_RETRIES

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT content FROM conversations WHERE role = 'evaluator_log' ORDER BY id"
        ).fetchall()

    cases: list[dict] = []
    for row in rows:
        try:
            payload = json.loads(row["content"])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("passed") is not False:
            continue
        if payload.get("attempts", 0) < MAX_EVAL_RETRIES:
            continue
        if not payload.get("user_message"):
            continue
        cases.append(payload)
    return cases


def get_session_messages(session_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT timestamp, role, content
            FROM conversations
            WHERE session_id = ? AND role IN ('user', 'assistant')
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]
