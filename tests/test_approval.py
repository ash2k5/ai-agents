"""Tests for the approval helpers and the pause/resume driver, using fakes."""

import asyncio
from types import SimpleNamespace

from ai_agents.approval import (
    CONFIRMATION_FUNCTION,
    approval_response,
    final_text,
    find_approval_request,
    run_order,
)


def part(text=None, fn_name=None, fn_id=None):
    call = SimpleNamespace(name=fn_name, id=fn_id) if fn_name else None
    return SimpleNamespace(text=text, function_call=call)


def event(parts, invocation_id="inv-1"):
    content = SimpleNamespace(parts=parts) if parts is not None else None
    return SimpleNamespace(content=content, invocation_id=invocation_id)


def test_find_approval_request_found():
    events = [event([part(fn_name=CONFIRMATION_FUNCTION, fn_id="appr-9")], "inv-7")]
    assert find_approval_request(events) == {
        "approval_id": "appr-9",
        "invocation_id": "inv-7",
    }


def test_find_approval_request_ignores_other_calls():
    events = [event([part(fn_name="place_shipping_order", fn_id="x")])]
    assert find_approval_request(events) is None


def test_find_approval_request_ignores_empty_content():
    assert find_approval_request([event(None), event([])]) is None


def test_find_approval_request_among_mixed_parts():
    events = [
        event([part(text="thinking")]),
        event(
            [part(text="more"), part(fn_name=CONFIRMATION_FUNCTION, fn_id="a")], "inv-2"
        ),
    ]
    assert find_approval_request(events)["invocation_id"] == "inv-2"


def test_approval_response_shape():
    content = approval_response("appr-1", True)
    assert content.role == "user"
    response = content.parts[0].function_response
    assert response.id == "appr-1"
    assert response.name == CONFIRMATION_FUNCTION
    assert response.response == {"confirmed": True}


def test_approval_response_reject():
    content = approval_response("appr-2", False)
    assert content.parts[0].function_response.response == {"confirmed": False}


def test_final_text_joins_and_strips():
    events = [event([part(text="Hello")]), event([part(text="world")])]
    assert final_text(events) == "Hello\nworld"


def test_final_text_ignores_non_text():
    events = [event([part(fn_name="x", fn_id="1")]), event(None)]
    assert final_text(events) == ""


def test_final_text_includes_intermediate_text():
    """Mid-stream (non-final) text is part of the result by design."""
    events = [
        event([part(text="Working on it...")]),
        event([part(fn_name="place_shipping_order", fn_id="1")]),
        event([part(text="Order approved.")]),
    ]
    result = final_text(events)
    assert "Working on it..." in result
    assert "Order approved." in result


class FakeSessions:
    async def create_session(self, **kwargs):
        return None


class FakeRunner:
    """Yields a first batch of events, then a second batch on resume."""

    def __init__(self, first, resumed=None):
        self.session_service = FakeSessions()
        self._batches = [first, resumed or []]
        self.calls = 0

    async def run_async(self, **kwargs):
        batch = self._batches[min(self.calls, 1)]
        self.calls += 1
        for item in batch:
            yield item


def test_run_order_no_approval_needed():
    runner = FakeRunner([event([part(text="Order placed")])])
    result = asyncio.run(run_order(runner, "Ship 3", approve=True, app_name="x"))
    assert result == "Order placed"
    assert runner.calls == 1


def test_run_order_resumes_after_approval():
    runner = FakeRunner(
        first=[event([part(fn_name=CONFIRMATION_FUNCTION, fn_id="a")], "inv-1")],
        resumed=[event([part(text="Order approved: ORD-10-HUMAN")])],
    )
    result = asyncio.run(run_order(runner, "Ship 10", approve=True, app_name="x"))
    assert result == "Order approved: ORD-10-HUMAN"
    assert runner.calls == 2
