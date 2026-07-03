import json
from collections import Counter
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from config import DASHBOARD_PASSWORD
from memory.db import get_connection
from styles import CHART_COLORS


# ---------------------------------------------------------------------------
# Raw data loaders
# ---------------------------------------------------------------------------

def _fetch_tool_entries() -> list[dict]:
    entries = []
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT session_id, timestamp, content FROM conversations WHERE role = 'tool_log' ORDER BY id"
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
                entries.append({"session_id": row["session_id"], "timestamp": row["timestamp"], "name": item, "arguments": {}})
            elif isinstance(item, dict):
                entries.append({
                    "session_id": row["session_id"],
                    "timestamp": row["timestamp"],
                    "name": item.get("name", ""),
                    "arguments": item.get("arguments", {}),
                })
    return entries


def _fetch_sessions() -> list[dict]:
    """One row per session: first message timestamp."""
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


def _fetch_guardrail_blocks() -> int:
    with get_connection() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM conversations WHERE role = 'guardrail_log'"
        ).fetchone()["n"]
    return n


def _fetch_evaluator_logs() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT content FROM conversations WHERE role = 'evaluator_log'"
        ).fetchall()
    results = []
    for row in rows:
        try:
            results.append(json.loads(row["content"]))
        except json.JSONDecodeError:
            continue
    return results


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
            SELECT substr(MIN(timestamp), 1, 10) AS day, COUNT(DISTINCT session_id) AS sessions
            FROM conversations
            WHERE role = 'user'
            GROUP BY session_id
            ORDER BY day DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


# ---------------------------------------------------------------------------
# Aggregated metrics
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30)
def load_metrics() -> dict:
    tool_entries = _fetch_tool_entries()
    sessions = _fetch_sessions()
    evaluator_logs = _fetch_evaluator_logs()
    guardrail_blocks = _fetch_guardrail_blocks()
    messages_per_day_raw = _fetch_user_messages_per_day()
    sessions_per_day_raw = _fetch_sessions_per_day()

    total_sessions = len(sessions)

    # Tool-level counters per session
    sessions_with_lead: set[str] = set()
    sessions_with_call: set[str] = set()
    sessions_with_unknown: set[str] = set()
    tool_counter: Counter = Counter()
    unknown_questions: list[str] = []
    ratings: list[int] = []

    for entry in tool_entries:
        name = entry["name"]
        sid = entry["session_id"]
        args = entry["arguments"]
        tool_counter[name] += 1
        if name == "record_user_details" and args.get("email"):
            sessions_with_lead.add(sid)
        elif name == "schedule_call_tool":
            sessions_with_call.add(sid)
        elif name == "record_unknown_question":
            sessions_with_unknown.add(sid)
            q = args.get("question")
            if q:
                unknown_questions.append(q)
        elif name == "record_feedback_tool":
            r = args.get("rating")
            if isinstance(r, int):
                ratings.append(r)

    # Evaluator stats
    with get_connection() as _conn:
        total_turns = _conn.execute(
            "SELECT COUNT(*) AS n FROM conversations WHERE role = 'user'"
        ).fetchone()["n"]
    retry_turns = sum(1 for e in evaluator_logs if e.get("attempts", 0) > 0)
    retry_rate = round(retry_turns / total_turns * 100, 1) if total_turns else 0.0

    unknown_rate = round(len(sessions_with_unknown) / total_sessions * 100, 1) if total_sessions else 0.0
    lead_rate = round(len(sessions_with_lead) / total_sessions * 100, 1) if total_sessions else 0.0

    feedback_avg = round(sum(ratings) / len(ratings), 2) if ratings else None

    # Conversion funnel: Sessions → Lead (email) → Call
    funnel = [
        {"etapa": "Sesiones", "n": total_sessions},
        {"etapa": "Interactuaron", "n": total_sessions},
        {"etapa": "Email compartido", "n": len(sessions_with_lead)},
        {"etapa": "Call agendada", "n": len(sessions_with_call)},
    ]

    # Top unknown questions (top 8)
    top_unknown = [
        {"pregunta": q, "veces": c}
        for q, c in Counter(unknown_questions).most_common(8)
    ]

    # Tool usage breakdown (rename for display)
    tool_display_names = {
        "record_unknown_question": "Sin respuesta",
        "record_user_details": "Email capturado",
        "schedule_call_tool": "Call agendada",
        "check_availability_tool": "Consulta disponibilidad",
        "record_feedback_tool": "Feedback recibido",
        "create_checklist": "Checklist creado",
        "mark_complete": "Checklist completado",
    }
    tool_usage = [
        {"herramienta": tool_display_names.get(k, k), "usos": v}
        for k, v in tool_counter.most_common()
    ]

    # Rating distribution
    rating_dist = [{"rating": str(i), "count": ratings.count(i)} for i in range(1, 6)]

    # Daily activity: merge sessions_per_day + messages_per_day by day
    day_map: dict[str, dict] = {}
    for r in messages_per_day_raw:
        day_map.setdefault(r["day"], {})["messages"] = r["messages"]
    for r in sessions_per_day_raw:
        day_map.setdefault(r["day"], {})["sessions"] = r["sessions"]
    daily_activity = sorted(
        [{"día": d, "mensajes": v.get("messages", 0), "sesiones": v.get("sessions", 0)} for d, v in day_map.items()],
        key=lambda x: x["día"],
    )[-14:]

    return {
        "total_sessions": total_sessions,
        "total_turns": total_turns,
        "lead_rate": lead_rate,
        "leads_count": len(sessions_with_lead),
        "calls_count": len(sessions_with_call),
        "feedback_avg": feedback_avg,
        "feedback_count": len(ratings),
        "retry_rate": retry_rate,
        "retry_turns": retry_turns,
        "unknown_rate": unknown_rate,
        "guardrail_blocks": guardrail_blocks,
        "funnel": funnel,
        "top_unknown": top_unknown,
        "tool_usage": tool_usage,
        "rating_dist": rating_dist,
        "daily_activity": daily_activity,
    }


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def _base_config(chart: alt.Chart) -> alt.Chart:
    return chart.configure_view(strokeWidth=0).configure_axis(
        labelColor="#8c8c95",
        titleColor="#8c8c95",
        gridColor="#2a2a32",
        domainColor="#2a2a32",
    ).configure_title(color="#ececef", fontSize=13, fontWeight=500)


def _daily_activity_chart(data: list[dict]) -> alt.Chart:
    if not data:
        return None
    df = pd.DataFrame(data)
    base = alt.Chart(df).encode(x=alt.X("día:O", title="Día", axis=alt.Axis(labelAngle=-30)))
    line_msgs = base.mark_line(strokeWidth=2, color=CHART_COLORS["blue"]).encode(
        y=alt.Y("mensajes:Q", title="Mensajes"),
        tooltip=["día", "mensajes"],
    )
    line_sess = base.mark_line(strokeWidth=2, strokeDash=[4, 4], color=CHART_COLORS["gold"]).encode(
        y=alt.Y("sesiones:Q", title="Sesiones"),
        tooltip=["día", "sesiones"],
    )
    return _base_config((line_msgs + line_sess).properties(title="Actividad diaria", height=260))


def _funnel_chart(data: list[dict]) -> alt.Chart:
    if not data:
        return None
    df = pd.DataFrame(data)
    chart = (
        alt.Chart(df)
        .mark_bar(color=CHART_COLORS["blue"], cornerRadiusEnd=4)
        .encode(
            y=alt.Y("etapa:N", sort=None, title=""),
            x=alt.X("n:Q", title="Sesiones"),
            tooltip=["etapa", "n"],
        )
        .properties(title="Embudo de conversión", height=160)
    )
    return _base_config(chart)


def _tool_usage_chart(data: list[dict]) -> alt.Chart:
    if not data:
        return None
    df = pd.DataFrame(data)
    chart = (
        alt.Chart(df)
        .mark_bar(color=CHART_COLORS["purple"], cornerRadiusEnd=4)
        .encode(
            y=alt.Y("herramienta:N", sort="-x", title=""),
            x=alt.X("usos:Q", title="Usos totales"),
            tooltip=["herramienta", "usos"],
        )
        .properties(title="Uso de herramientas", height=200)
    )
    return _base_config(chart)


def _unknown_chart(data: list[dict]) -> alt.Chart:
    if not data:
        return None
    df = pd.DataFrame(data)
    chart = (
        alt.Chart(df)
        .mark_bar(color=CHART_COLORS["gold"], cornerRadiusEnd=4)
        .encode(
            y=alt.Y("pregunta:N", sort="-x", title=""),
            x=alt.X("veces:Q", title="Veces"),
            tooltip=["pregunta", "veces"],
        )
        .properties(title="Top preguntas sin respuesta", height=220)
    )
    return _base_config(chart)


def _rating_chart(data: list[dict]) -> alt.Chart:
    if not data or all(d["count"] == 0 for d in data):
        return None
    df = pd.DataFrame(data)
    chart = (
        alt.Chart(df)
        .mark_bar(color=CHART_COLORS["gold"], cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("rating:N", title="Puntuación"),
            y=alt.Y("count:Q", title="Respuestas"),
            tooltip=["rating", "count"],
        )
        .properties(title="Distribución de feedback", height=200)
    )
    return _base_config(chart)


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_analytics() -> None:
    if not DASHBOARD_PASSWORD:
        st.warning("Configurá `DASHBOARD_PASSWORD` en tu `.env` para acceder al dashboard.")
        return

    if not st.session_state.get("analytics_unlocked"):
        st.markdown("### Analytics internas — acceso restringido")
        password = st.text_input("Contraseña", type="password", key="analytics_password")
        if st.button("Ingresar", key="analytics_unlock"):
            if password == DASHBOARD_PASSWORD:
                st.session_state.analytics_unlocked = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        return

    if st.button("Actualizar métricas", key="analytics_refresh"):
        load_metrics.clear()
        st.rerun()

    m = load_metrics()

    # --- Row 1: engagement & leads ---
    st.markdown("#### Alcance y conversión")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sesiones", m["total_sessions"])
    c2.metric("Mensajes recibidos", m["total_turns"])
    c3.metric(
        "Conversión a lead",
        f"{m['lead_rate']}%",
        f"{m['leads_count']} emails",
    )
    c4.metric("Calls agendadas", m["calls_count"])

    # --- Row 2: quality & safety ---
    st.markdown("#### Calidad y seguridad")
    c5, c6, c7, c8 = st.columns(4)
    if m["feedback_avg"] is None:
        c5.metric("Feedback promedio", "—", "Sin valoraciones")
    else:
        c5.metric(
            "Feedback promedio",
            f"{m['feedback_avg']} / 5",
            f"{m['feedback_count']} respuestas",
        )
    c6.metric(
        "Reintentos evaluador",
        f"{m['retry_rate']}%",
        f"{m['retry_turns']} turnos",
    )
    c7.metric(
        "Preguntas sin respuesta",
        f"{m['unknown_rate']}%",
        "del total de sesiones",
    )
    c8.metric("Mensajes bloqueados", m["guardrail_blocks"])

    st.divider()

    # --- Daily activity ---
    daily_chart = _daily_activity_chart(m["daily_activity"])
    if daily_chart:
        st.altair_chart(daily_chart, use_container_width=True)
        st.caption("— Mensajes totales  · · · Sesiones nuevas")
    else:
        st.info("Sin actividad diaria registrada.")

    st.divider()

    # --- Funnel + Tool usage ---
    col_left, col_right = st.columns(2)
    with col_left:
        funnel_chart = _funnel_chart(m["funnel"])
        if funnel_chart:
            st.altair_chart(funnel_chart, use_container_width=True)
        else:
            st.info("Sin datos de embudo.")

    with col_right:
        tool_chart = _tool_usage_chart(m["tool_usage"])
        if tool_chart:
            st.altair_chart(tool_chart, use_container_width=True)
        else:
            st.info("Sin llamadas a herramientas registradas.")

    st.divider()

    # --- Unknown questions + Feedback distribution ---
    col_a, col_b = st.columns(2)
    with col_a:
        unk_chart = _unknown_chart(m["top_unknown"])
        if unk_chart:
            st.altair_chart(unk_chart, use_container_width=True)
        else:
            st.info("Sin preguntas sin responder registradas.")

    with col_b:
        rat_chart = _rating_chart(m["rating_dist"])
        if rat_chart:
            st.altair_chart(rat_chart, use_container_width=True)
        else:
            st.info("Sin valoraciones de feedback registradas.")

    # --- Raw tables ---
    with st.expander("Ver datos en tablas"):
        t1, t2, t3 = st.tabs(["Actividad diaria", "Herramientas", "Sin responder"])
        with t1:
            st.dataframe(pd.DataFrame(m["daily_activity"]), use_container_width=True, hide_index=True)
        with t2:
            st.dataframe(pd.DataFrame(m["tool_usage"]) if m["tool_usage"] else pd.DataFrame(), use_container_width=True, hide_index=True)
        with t3:
            st.dataframe(pd.DataFrame(m["top_unknown"]) if m["top_unknown"] else pd.DataFrame(), use_container_width=True, hide_index=True)
