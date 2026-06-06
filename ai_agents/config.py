"""Runtime configuration, sourced from the environment.

The Gemini API key is never stored in code. ADK reads ``GOOGLE_API_KEY`` from the
environment (or a local ``.env`` file) at call time; ``require_api_key`` is used by
runnable entrypoints to fail fast with a clear message when it is missing.
"""

from __future__ import annotations

import os

from google.adk.models.google_llm import Gemini
from google.genai import types

DEFAULT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_DB_PATH = "agent_sessions.db"
LARGE_ORDER_THRESHOLD = 5

_RETRYABLE_STATUS_CODES = (429, 500, 503, 504)


def model_name() -> str:
    return os.environ.get("GOOGLE_MODEL", "").strip() or DEFAULT_MODEL


def retry_options() -> types.HttpRetryOptions:
    return types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=list(_RETRYABLE_STATUS_CODES),
    )


def build_model() -> Gemini:
    return Gemini(model=model_name(), retry_options=retry_options())


def db_url() -> str:
    path = os.environ.get("ADK_DB_PATH", "").strip() or DEFAULT_DB_PATH
    return f"sqlite:///{path}"


def require_api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key, "
            "or export GOOGLE_API_KEY before running."
        )
    return key
