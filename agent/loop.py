import json
import uuid

from agent.evaluator import OPERATIONAL_TOOLS, evaluate_response, is_operational_turn, tool_names
from agent.guardrails import guard_message
from config import MAX_EVAL_RETRIES, MAX_RESPONSE_WORDS, TWIN_NAME
from context import EVALUATOR_CONTEXT, get_twin_system_prompt
from improver.generate import regenerate_behavior_addendum
from llm_client import chat_completion
from memory.repository import save_turn
from tools import tools
from tools.checklist import create_checklist, mark_complete
from tools.contact import record_unknown_question, record_user_details
from tools.feedback import record_feedback_tool
from tools.scheduling import check_availability_tool, schedule_call_tool
from tools.session_state import bind_session_state


def _default_session_state() -> dict:
    return {"session_id": None, "checklist": [], "completed": []}


def _ensure_session_id(session_state: dict) -> str:
    if not session_state.get("session_id"):
        session_state["session_id"] = str(uuid.uuid4())
        print(f"[Memory] New session: {session_state['session_id']}", flush=True)
    return session_state["session_id"]


def _record_rejection(
    rejections: list[dict],
    response: str,
    feedback: str,
    tools_used: list | None,
) -> None:
    rejections.append(
        {
            "attempt": len(rejections) + 1,
            "response": response,
            "feedback": feedback,
            "tools_used": sorted(tool_names(tools_used)),
        }
    )


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
    messages = [{"role": "system", "content": get_twin_system_prompt()}]
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

    rejections: list[dict] = []
    if not evaluation["pass"]:
        _record_rejection(rejections, response, evaluation["feedback"], tools_used)

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
        if not evaluation["pass"]:
            _record_rejection(rejections, response, evaluation["feedback"], tools_used)
        attempts += 1

    max_retries_exceeded = not evaluation["pass"] and attempts >= MAX_EVAL_RETRIES

    if evaluation["pass"] and attempts > 0:
        print(f"[Evaluator] Passed on attempt {attempts + 1}", flush=True)
    elif max_retries_exceeded:
        print(
            f"[Evaluator] Max retries reached. Last feedback: {evaluation['feedback']}",
            flush=True,
        )

    evaluator_detail = None
    if max_retries_exceeded:
        evaluator_detail = {
            "attempts": attempts,
            "passed": False,
            "max_retries_exceeded": True,
            "user_message": message,
            "final_response": response,
            "rejections": rejections,
        }

    save_turn(
        session_id,
        message,
        response,
        tools_used=tools_used or None,
        evaluator_attempts=attempts,
        evaluator_passed=evaluation["pass"],
        evaluator_detail=evaluator_detail,
    )

    if max_retries_exceeded:
        try:
            regenerate_behavior_addendum()
        except Exception as exc:
            print(f"[Improver] Failed to regenerate addendum: {exc}", flush=True)

    return response, session_state
