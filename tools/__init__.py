from tools.checklist import create_checklist_json, mark_complete_json
from tools.contact import record_unknown_question_json, record_user_details_json
from tools.feedback import record_feedback_tool_json
from tools.scheduling import check_availability_tool_json, schedule_call_tool_json

tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": record_unknown_question_json},
    {"type": "function", "function": record_feedback_tool_json},
    {"type": "function", "function": check_availability_tool_json},
    {"type": "function", "function": schedule_call_tool_json},
    {"type": "function", "function": create_checklist_json},
    {"type": "function", "function": mark_complete_json},
]
