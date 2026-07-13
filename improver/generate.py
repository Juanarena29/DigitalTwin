"""Generate behavior rules from evaluator max-retry failures."""

from __future__ import annotations

from config import IMPROVER_MODEL, MAX_EVAL_RETRIES, TWIN_NAME
from improver.addendum import load_behavior_addendum, save_behavior_addendum
from llm_client import chat_completion
from memory.repository import fetch_max_retry_failures

_IMPROVER_PROMPT = """\
You improve a digital twin's BEHAVIOR instructions only.

STRICT RULES:
- Do NOT add new facts about {name} (no names, dates, relationships, companies, etc.).
- Approved facts live only in summary + LinkedIn — you cannot change those.
- Output only behavioral rules: when to call record_unknown_question, how to decline,
  redirect off-topic questions, tone, brevity, tool usage order.
- Write in clear Spanish, imperative style, bullet points grouped by theme.
- Keep it under 400 words. Skip redundant rules already implied by strict grounding.
- If failures share a pattern, merge into one rule — do not repeat per example.

Below are real turns where the quality evaluator rejected the response {max_retries} times.
Extract durable behavior rules so similar questions are handled correctly next time.

# Failures
{failures}

Output ONLY the addendum body (no markdown heading like "# Ajustes").\
"""


def count_max_retry_failures() -> int:
    return len(fetch_max_retry_failures())


def _format_failures(cases: list[dict]) -> str:
    blocks = []
    for i, case in enumerate(cases, start=1):
        rejections = case.get("rejections") or []
        lines = [f"## Failure {i}", f"User question: {case.get('user_message', '')}"]
        for rej in rejections:
            n = rej.get("attempt", "?")
            lines.append(f"- Attempt {n} rejected: {rej.get('feedback', '')}")
            if rej.get("response"):
                lines.append(f"  Draft: {rej['response'][:500]}")
            if rej.get("tools_used"):
                lines.append(f"  Tools: {', '.join(rej['tools_used'])}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def regenerate_behavior_addendum() -> str:
    cases = fetch_max_retry_failures()
    if not cases:
        save_behavior_addendum("")
        return ""

    prompt = _IMPROVER_PROMPT.format(
        name=TWIN_NAME,
        max_retries=MAX_EVAL_RETRIES,
        failures=_format_failures(cases),
    )
    response = chat_completion(
        [{"role": "user", "content": prompt}],
        model=IMPROVER_MODEL,
    )
    addendum = (response.choices[0].message.content or "").strip()
    save_behavior_addendum(addendum)
    print(f"[Improver] Regenerated behavior addendum from {len(cases)} failure(s)", flush=True)
    return addendum


def get_behavior_addendum() -> str:
    return load_behavior_addendum()
