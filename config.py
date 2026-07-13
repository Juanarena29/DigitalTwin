from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SUMMARY_PATH = DATA_DIR / "summary.txt"
LINKEDIN_PATH = DATA_DIR / "linkedin.pdf"
DB_PATH = DATA_DIR / "twin.db"
BEHAVIOR_ADDENDUM_PATH = DATA_DIR / "behavior_addendum.txt"

MODEL_NAME = "gpt-4o-mini"
EVALUATOR_MODEL = "gpt-4o-mini"
GUARDRAIL_MODEL = "gpt-4o-mini"
IMPROVER_MODEL = "gpt-4o-mini"
MAX_EVAL_RETRIES = 3
MAX_RESPONSE_WORDS = 100

RATE_LIMIT_MAX_MESSAGES = 20
RATE_LIMIT_WINDOW_SECONDS = 300

TWIN_NAME = "Juan Ignacio Arena"
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")

BLOCKED_REPLY = (
    "Lo siento, no puedo procesar ese mensaje. "
    "¿Hay algo relacionado a mi carrera que querés saber?"
)
RATE_LIMIT_REPLY = (
    "Estás enviando muchos mensajes seguidos. Probá de nuevo en unos minutos."
)
