import json
import uuid

from agent.evaluator import OPERATIONAL_TOOLS, evaluate_response, is_operational_turn, tool_names
from agent.guardrails import guard_message
from config import MAX_EVAL_RETRIES, MAX_RESPONSE_WORDS, TWIN_NAME
from context import EVALUATOR_CONTEXT, TWIN_SYSTEM_PROMPT
from llm_client import chat_completion
from memory.repository import save_turn
from tools import tools
from tools.checklist import create_checklist, mark_complete
from tools.contact import record_unknown_question, record_user_details
from tools.feedback import record_feedback_tool
from tools.scheduling import check_availability_tool, schedule_call_tool
from tools.session_state import bind_session_state

_system = [{"role": "system", "content": TWIN_SYSTEM_PROMPT}]


def _default_session_state() -> dict:
    return {"session_id": None, "checklist": [], "completed": []}


def _ensure_session_id(session_state: dict) -> str:
    if not session_state.get("session_id"):
        session_state["session_id"] = str(uuid.uuid4())
        print(f"[Memory] New session: {session_state['session_id']}", flush=True)
    return session_state["session_id"]


def handle_tool_calls(tool_calls):
    results = []
    tools_used = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        tools_used.append({"name": tool_name, "arguments": arguments})
        print(f"Tool called: {tool_name}", flush=True)
        tool = globals().get(tool_name)
        result = tool(**arguments) if tool else f"Unknown tool: {tool_name}"
        results.append(
            {"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id}
        )
    return results, tools_used


def generate_response(message, history, feedback=None, operational_context=False):
    messages = list(_system)
    if feedback:
        if operational_context:
            revision = (
                f"Your previous draft was rejected. Reason: {feedback} "
                f"Rewrite in first person as {TWIN_NAME}. "
                f"Keep it under {MAX_RESPONSE_WORDS} words. "
                "This is a scheduling/contact reply — confirm details briefly, no career essay."
            )
        else:
            revision = (
                f"Your previous draft was rejected. Reason: {feedback} "
                f"STRICT GROUNDING: only use facts from your approved summary and LinkedIn. "
                f"If the answer is not there, call record_unknown_question first, then say "
                f"that info is not in your profile. Never invent. "
                f"Rewrite in first person as {TWIN_NAME}, under {MAX_RESPONSE_WORDS} words."
            )
        messages.append({"role": "system", "content": revision})
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    tools_used = []
    response = chat_completion(messages, tools=tools)
    while response.choices[0].finish_reason == "tool_calls":
        message_obj = response.choices[0].message
        results, turn_tools = handle_tool_calls(message_obj.tool_calls)
        tools_used.extend(turn_tools)
        messages.append(message_obj)
        messages.extend(results)
        response = chat_completion(messages, tools=tools)
    return response.choices[0].message.content, tools_used


def chat(message, history, session_state=None):
    if not session_state or "checklist" not in session_state:
        session_state = _default_session_state()
    bind_session_state(session_state)
    session_id = _ensure_session_id(session_state)

    allowed, blocked_reply = guard_message(message, session_id)
    if not allowed:
        return blocked_reply, session_state

    operational_context = is_operational_turn(message, history)
    response, tools_used = generate_response(message, history)
    evaluation = evaluate_response(
        message, response, EVALUATOR_CONTEXT, tools_used, history
    )

    attempts = 0
    while not evaluation["pass"] and attempts < MAX_EVAL_RETRIES:
        if OPERATIONAL_TOOLS.intersection(tool_names(tools_used)):
            break
        print(
            f"[Evaluator] Rejected (attempt {attempts + 1}): {evaluation['feedback']}",
            flush=True,
        )
        response, tools_used = generate_response(
            message,
            history,
            feedback=evaluation["feedback"],
            operational_context=operational_context,
        )
        evaluation = evaluate_response(
            message, response, EVALUATOR_CONTEXT, tools_used, history
        )
        attempts += 1

    if evaluation["pass"] and attempts > 0:
        print(f"[Evaluator] Passed on attempt {attempts + 1}", flush=True)
    elif not evaluation["pass"]:
        print(
            f"[Evaluator] Max retries reached. Last feedback: {evaluation['feedback']}",
            flush=True,
        )

    save_turn(
        session_id,
        message,
        response,
        tools_used=tools_used or None,
        evaluator_attempts=attempts,
        evaluator_passed=evaluation["pass"],
    )

    return response, session_state
