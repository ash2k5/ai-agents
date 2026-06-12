"""Runtime configuration, sourced from the environment.

The Gemini API key is never stored in code. ADK reads ``GOOGLE_API_KEY`` from the
environment (or a local ``.env`` file) at call time; ``require_api_key`` is used by
runnable entrypoints to fail fast with a clear message when it is missing.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import platformdirs
from google.adk.models.google_llm import Gemini
from google.genai import types

DEFAULT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_DB_FILENAME = "agent_sessions.db"
DEFAULT_LARGE_ORDER_THRESHOLD = 5

_RETRYABLE_STATUS_CODES = (429, 500, 503, 504)
_MODEL_PATTERN = re.compile(r"(?:models/)?gemini-[a-z0-9.\-]+")


def model_name() -> str:
    name = os.environ.get("GOOGLE_MODEL", "").strip() or DEFAULT_MODEL
    if not _MODEL_PATTERN.fullmatch(name):
        raise SystemExit(
            f"GOOGLE_MODEL '{name}' is not a recognized Gemini model id. "
            "Set it to a gemini-* model (e.g. gemini-2.5-flash-lite) or unset it."
        )
    return name


def retry_options() -> types.HttpRetryOptions:
    return types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=list(_RETRYABLE_STATUS_CODES),
    )


def build_model() -> Gemini:
    return Gemini(model=model_name(), retry_options=retry_options())


def order_threshold() -> int:
    raw = os.environ.get("LARGE_ORDER_THRESHOLD", "").strip()
    if not raw:
        return DEFAULT_LARGE_ORDER_THRESHOLD
    try:
        value = int(raw)
    except ValueError:
        raise SystemExit(f"LARGE_ORDER_THRESHOLD '{raw}' is not an integer.") from None
    if value < 0:
        raise SystemExit("LARGE_ORDER_THRESHOLD must be non-negative.")
    return value


def db_path() -> Path:
    override = os.environ.get("ADK_DB_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    data_dir = platformdirs.user_data_dir("ai_agents", appauthor=False)
    return Path(data_dir) / DEFAULT_DB_FILENAME


def db_url() -> str:
    return f"sqlite:///{db_path().as_posix()}"


def require_api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key, "
            "or export GOOGLE_API_KEY before running."
        )
    return key
