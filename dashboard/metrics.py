"""Load and aggregate analytics metrics from the conversation database."""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass

import pandas as pd

from config import DASHBOARD_PASSWORD
from memory.db import get_connection

_METRICS_TTL_SECONDS = 30
_metrics_cache: DashboardData | None = None
_metrics_cached_at: float = 0.0

_EMPTY_DAILY = pd.DataFrame(columns=["día", "métrica", "valor"])
_EMPTY_UNKNOWN = pd.DataFrame(columns=["pregunta", "veces"])
_EMPTY_RATINGS = pd.DataFrame(columns=["rating", "count"])


@dataclass(frozen=True)
class DashboardData:
    sessions: int
    lead_rate: float
    leads_count: int
    calls_count: int
    unknown_rate: float
    daily: pd.DataFrame
    unknown: pd.DataFrame
    ratings: pd.DataFrame


def dashboard_password_configured() -> bool:
    return bool(DASHBOARD_PASSWORD)


def clear_metrics_cache() -> None:
    global _metrics_cache, _metrics_cached_at
    _metrics_cache = None
    _metrics_cached_at = 0.0


def load_metrics(*, force: bool = False) -> DashboardData:
    global _metrics_cache, _metrics_cached_at
    now = time.time()
    if (
        not force
        and _metrics_cache is not None
        and now - _metrics_cached_at < _METRICS_TTL_SECONDS
    ):
        return _metrics_cache

    data = _compute_metrics()
    _metrics_cache = data
    _metrics_cached_at = now
    return data


def _compute_metrics() -> DashboardData:
    tool_entries = _fetch_tool_entries()
    sessions = _fetch_sessions()
    messages_per_day = _fetch_user_messages_per_day()
    sessions_per_day = _fetch_sessions_per_day()

    total_sessions = len(sessions)
    sessions_with_lead: set[str] = set()
    sessions_with_call: set[str] = set()
    sessions_with_unknown: set[str] = set()
    unknown_questions: list[str] = []
    ratings: list[int] = []

    for entry in tool_entries:
        name = entry["name"]
        sid = entry["session_id"]
        args = entry["arguments"]
        if name == "record_user_details" and args.get("email"):
            sessions_with_lead.add(sid)
        elif name == "schedule_call_tool":
            sessions_with_call.add(sid)
        elif name == "record_unknown_question":
            sessions_with_unknown.add(sid)
            if q := args.get("question"):
                unknown_questions.append(q)
        elif name == "record_feedback_tool":
            if isinstance(r := args.get("rating"), int):
                ratings.append(r)

    unknown_rate = (
        round(len(sessions_with_unknown) / total_sessions * 100, 1)
        if total_sessions
        else 0.0
    )
    lead_rate = (
        round(len(sessions_with_lead) / total_sessions * 100, 1)
        if total_sessions
        else 0.0
    )

    day_map: dict[str, dict[str, int]] = {}
    for row in messages_per_day:
        day_map.setdefault(row["day"], {})["messages"] = row["messages"]
    for row in sessions_per_day:
        day_map.setdefault(row["day"], {})["sessions"] = row["sessions"]

    daily_rows: list[dict] = []
    for day in sorted(day_map):
        values = day_map[day]
        daily_rows.append(
            {"día": day, "métrica": "Mensajes", "valor": values.get("messages", 0)}
        )
        daily_rows.append(
            {"día": day, "métrica": "Sesiones", "valor": values.get("sessions", 0)}
        )

    daily = pd.DataFrame(daily_rows)
    if daily.empty:
        daily = _EMPTY_DAILY.copy()
    else:
        daily = daily.iloc[-28:]

    unknown = pd.DataFrame(
        [
            {"pregunta": question, "veces": count}
            for question, count in Counter(unknown_questions).most_common(8)
        ]
    )
    if unknown.empty:
        unknown = _EMPTY_UNKNOWN.copy()

    ratings_df = pd.DataFrame(
        [{"rating": str(i), "count": ratings.count(i)} for i in range(1, 6)]
    )
    if ratings_df["count"].sum() == 0:
        ratings_df = _EMPTY_RATINGS.copy()

    return DashboardData(
        sessions=total_sessions,
        lead_rate=lead_rate,
        leads_count=len(sessions_with_lead),
        calls_count=len(sessions_with_call),
        unknown_rate=unknown_rate,
        daily=daily,
        unknown=unknown,
        ratings=ratings_df,
    )


def _fetch_tool_entries() -> list[dict]:
    entries: list[dict] = []
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT session_id, content FROM conversations WHERE role = 'tool_log' ORDER BY id"
        ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["content"])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, list):
            continue
        for item in payload:
            if isinstance(item, str):
                entries.append(
                    {"session_id": row["session_id"], "name": item, "arguments": {}}
                )
            elif isinstance(item, dict):
                entries.append(
                    {
                        "session_id": row["session_id"],
                        "name": item.get("name", ""),
                        "arguments": item.get("arguments", {}),
                    }
                )
    return entries


def _fetch_sessions() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT session_id, MIN(timestamp) AS started_at
            FROM conversations
            WHERE role = 'user'
            GROUP BY session_id
            ORDER BY started_at
            """
        ).fetchall()
    return [dict(r) for r in rows]


def _fetch_user_messages_per_day(limit: int = 14) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT substr(timestamp, 1, 10) AS day, COUNT(*) AS messages
            FROM conversations
            WHERE role = 'user'
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _fetch_sessions_per_day(limit: int = 14) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT substr(timestamp, 1, 10) AS day, COUNT(DISTINCT session_id) AS sessions
            FROM conversations
            WHERE role = 'user'
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]
