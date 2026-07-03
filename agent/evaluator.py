import json
import re

from config import EVALUATOR_MODEL, MAX_RESPONSE_WORDS, TWIN_NAME
from llm_client import chat_completion

STRICT_GROUNDING_CRITERIA = f"""
STRICT GROUNDING (highest priority):
The twin may ONLY state facts explicitly present in the approved context below.
FAIL if the response includes ANY specific fact, number, date, name, company, project, skill, title,
certification, salary, grade, or claim about {TWIN_NAME} that is NOT clearly supported by the context.
FAIL on inference, guessing, or "plausible" additions — even if they sound reasonable.
FAIL if the user asked for missing info and the twin answered with invented content instead of
calling record_unknown_question and declining.
FAIL if the twin said it doesn't know / doesn't have the info but did NOT use record_unknown_question
(check tools used this turn).
Dates/times/emails from scheduling tools used this turn are allowed.

OTHER CRITERIA:
- OUT OF CHARACTER: generic AI assistant, impartial counselor, third person about {TWIN_NAME}
- TOO GENERIC: impersonal vocational templates without citing approved facts
- OFF TOPIC: unrelated content without redirect (except scheduling/contact/feedback flows)
- UNPROFESSIONAL TONE
- TOO LONG: over {MAX_RESPONSE_WORDS} words or essay-like
"""

AGE_QUESTION_PATTERN = re.compile(
    r"\b(edad|años|año|cuántos años|cuantos años|how old|age|nació|nacimiento|birth)\b",
    re.IGNORECASE,
)
AGE_CLAIM_PATTERNS = (
    re.compile(r"\b\d{1,2}\s*años\b", re.IGNORECASE),
    re.compile(r"\bnació en \d{4}\b", re.IGNORECASE),
    re.compile(r"\btiene \d{1,2}\b", re.IGNORECASE),
    re.compile(r"\bborn in \d{4}\b", re.IGNORECASE),
)
CONTEXT_AGE_PATTERN = re.compile(
    r"\b(edad|años|nació|nacimiento|born|years old)\b",
    re.IGNORECASE,
)
UNSURE_PATTERN = re.compile(
    r"\b("
    r"no (lo )?s[eé]|no tengo|no figure|no consta|no está|no disponible|"
    r"don't know|not in my profile|no tengo esa info|no tengo esa información"
    r")\b",
    re.IGNORECASE,
)

OPERATIONAL_TOOLS = frozenset({
    "check_availability_tool",
    "schedule_call_tool",
    "record_user_details",
    "record_feedback_tool",
})

SCHEDULING_HINTS = (
    "llamada",
    "call",
    "agendar",
    "disponib",
    "horario",
    "reunión",
    "reunion",
    "meeting",
    "schedule",
    "correo",
    "email",
    "@",
    "programar",
    "coordin",
)


def _word_count(text: str) -> int:
    return len(text.split())


def _conversation_text(user_message: str, history: list | None) -> str:
    parts = [user_message.lower()]
    for msg in (history or [])[-8:]:
        if isinstance(msg, dict):
            parts.append(str(msg.get("content", "")).lower())
    return " ".join(parts)


def is_operational_turn(user_message: str, history: list | None) -> bool:
    text = _conversation_text(user_message, history)
    return any(hint in text for hint in SCHEDULING_HINTS)


def tool_names(tools_used: list | None) -> set[str]:
    names: set[str] = set()
    for item in tools_used or []:
        if isinstance(item, str):
            names.add(item)
        elif isinstance(item, dict):
            name = item.get("name")
            if name:
                names.add(name)
    return names


def _operational_pass(candidate_response: str, tools_used: list | None) -> dict | None:
    if tools_used and OPERATIONAL_TOOLS.intersection(tool_names(tools_used)):
        words = _word_count(candidate_response)
        if words <= MAX_RESPONSE_WORDS:
            return {"pass": True, "feedback": ""}
        return {
            "pass": False,
            "feedback": (
                f"Response is {words} words; keep confirmation under {MAX_RESPONSE_WORDS}. "
                "Be brief: date, time, email, done."
            ),
        }
    return None


def _context_supports_age(context: str) -> bool:
    lower = context.lower()
    return bool(CONTEXT_AGE_PATTERN.search(lower))


def _claims_age(response: str) -> bool:
    return any(pattern.search(response) for pattern in AGE_CLAIM_PATTERNS)


def _check_age_hallucination(
    user_message: str,
    candidate_response: str,
    context: str,
    tools_used: list | None,
) -> dict | None:
    if not AGE_QUESTION_PATTERN.search(user_message):
        return None
    if _context_supports_age(context):
        return None
    if _claims_age(candidate_response):
        return {
            "pass": False,
            "feedback": (
                "Age/birth year is not in approved context. Do NOT invent. "
                "Call record_unknown_question, then say that info is not in your profile."
            ),
        }
    return _check_missing_unknown_tool(candidate_response, tools_used)


def _check_missing_unknown_tool(
    candidate_response: str,
    tools_used: list | None,
) -> dict | None:
    if "record_unknown_question" in tool_names(tools_used):
        return None
    if UNSURE_PATTERN.search(candidate_response):
        return {
            "pass": False,
            "feedback": (
                "You indicated missing info but did not call record_unknown_question. "
                "Call the tool first, then tell the user the fact is not in your profile."
            ),
        }
    return None


def evaluate_response(
    user_message: str,
    candidate_response: str,
    context: str,
    tools_used: list | None = None,
    history: list | None = None,
) -> dict:
    operational = _operational_pass(candidate_response, tools_used)
    if operational is not None:
        return operational

    words = _word_count(candidate_response)
    if words > MAX_RESPONSE_WORDS:
        return {
            "pass": False,
            "feedback": (
                f"Response is {words} words; keep it under {MAX_RESPONSE_WORDS}. "
                "Rewrite in 2-4 short sentences."
            ),
        }

    if is_operational_turn(user_message, history):
        return {"pass": True, "feedback": ""}

    age_check = _check_age_hallucination(user_message, candidate_response, context, tools_used)
    if age_check is not None:
        return age_check

    missing_tool = _check_missing_unknown_tool(candidate_response, tools_used)
    if missing_tool is not None:
        return missing_tool

    tools_note = ""
    if tools_used:
        tools_note = f"\n# Tools used this turn: {', '.join(sorted(tool_names(tools_used)))}\n"

    prompt = f"""You are a strict quality gate for {TWIN_NAME}'s digital twin.

The owner controls exactly what this twin may say — only facts in the approved context below.
When unsure whether a fact is in context, FAIL the response.

{tools_note}
# APPROVED CONTEXT (only allowed facts):
{context}

# Criteria — fail if ANY apply:
{STRICT_GROUNDING_CRITERIA}

# User question:
{user_message}

# Candidate response ({words} words):
{candidate_response}

Be strict. If any fact looks invented or inferred, fail.
Respond with JSON only: {{"pass": true or false, "feedback": "brief reason if fail, else empty string"}}"""

    response = chat_completion(
        [{"role": "user", "content": prompt}],
        model=EVALUATOR_MODEL,
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        return {
            "pass": bool(result.get("pass")),
            "feedback": result.get("feedback", ""),
        }
    except (json.JSONDecodeError, TypeError):
        print("[Evaluator] Failed to parse response, rejecting answer", flush=True)
        return {
            "pass": False,
            "feedback": "Evaluator could not verify grounding. Reply only with approved context facts.",
        }
