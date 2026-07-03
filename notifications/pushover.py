import os

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def push(text: str) -> None:
    requests.post(
        PUSHOVER_URL,
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        },
    )
