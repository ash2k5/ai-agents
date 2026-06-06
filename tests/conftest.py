"""Shared test fixtures and offline fakes.

A dummy API key is set before any ``ai_agents`` import so that constructing the agent
(which builds a Gemini model) never requires a real credential. No test makes a live call.
"""

import os

os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-real")

import pytest


class FakeConfirmation:
    def __init__(self, confirmed: bool):
        self.confirmed = confirmed


class FakeToolContext:
    """Stands in for ADK's ToolContext: a state dict plus the approval hooks."""

    def __init__(self, state=None, tool_confirmation=None):
        self.state = dict(state or {})
        self.tool_confirmation = tool_confirmation
        self.requested = None

    def request_confirmation(self, *, hint, payload):
        self.requested = {"hint": hint, "payload": payload}


@pytest.fixture
def make_ctx():
    def _make(state=None, tool_confirmation=None):
        return FakeToolContext(state=state, tool_confirmation=tool_confirmation)

    return _make


@pytest.fixture
def confirmation():
    return FakeConfirmation
