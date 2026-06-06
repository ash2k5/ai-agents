"""Resumable App and Runner wiring.

The App is marked resumable so the shipping approval workflow can pause for a human
decision and resume. Sessions persist in SQLite so an order awaiting approval survives a
restart.
"""

from __future__ import annotations

from google.adk.apps import App, ResumabilityConfig
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService

from .agent import root_agent
from .config import db_url

APP_NAME = "commerce_assistant"

app = App(
    name=APP_NAME,
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)


def build_runner(session_service: BaseSessionService | None = None) -> Runner:
    if session_service is None:
        from google.adk.sessions import DatabaseSessionService

        session_service = DatabaseSessionService(db_url=db_url())
    return Runner(app=app, session_service=session_service)
