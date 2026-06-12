"""Integration test: the approval pause/resume through a real ADK Runner.

A stub model emits the ``place_shipping_order`` call, lets ADK's confirmation flow pause,
and on resume summarizes the real tool result. This exercises the ``request_confirmation``
and ``invocation_id`` round-trip that the FakeRunner tests in ``test_approval.py`` cannot.
"""

import asyncio

import pytest
from google.adk.agents import LlmAgent
from google.adk.apps import App, ResumabilityConfig
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from ai_agents.app import APP_NAME
from ai_agents.approval import (
    CONFIRMATION_FUNCTION,
    approval_response,
    find_approval_request,
    run_order,
)
from ai_agents.tools import place_shipping_order

ORDER = "Ship 10 containers to Rotterdam"


def _order_response(contents) -> dict | None:
    for content in contents:
        for part in content.parts or []:
            fr = getattr(part, "function_response", None)
            if fr and fr.name == "place_shipping_order":
                return fr.response
    return None


class StubModel(BaseLlm):
    """Emits the order call first, then a summary once the tool result comes back."""

    model: str = "stub-model"

    async def generate_content_async(self, llm_request, stream=False):
        contents = llm_request.contents or []
        response = _order_response(contents)
        if response is not None:
            text = f"Order {response['status']}: {response.get('order_id', '')}".strip()
            yield LlmResponse(
                content=types.Content(role="model", parts=[types.Part(text=text)])
            )
            return
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            name="place_shipping_order",
                            args={"num_containers": 10, "destination": "Rotterdam"},
                        )
                    )
                ],
            )
        )


def _stub_runner() -> Runner:
    agent = LlmAgent(
        name="commerce_assistant",
        model=StubModel(),
        instruction="Place shipping orders.",
        tools=[place_shipping_order],
    )
    app = App(
        name=APP_NAME,
        root_agent=agent,
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
    return Runner(app=app, session_service=InMemorySessionService())


async def _drive(runner, approve):
    sessions = runner.session_service
    session_id = "order-it"
    await sessions.create_session(
        app_name=APP_NAME, user_id="user", session_id=session_id
    )
    message = types.Content(role="user", parts=[types.Part(text=ORDER)])
    paused = [
        e
        async for e in runner.run_async(
            user_id="user", session_id=session_id, new_message=message
        )
    ]
    request = find_approval_request(paused)
    if request is None:
        return paused, request, []
    resumed = [
        e
        async for e in runner.run_async(
            user_id="user",
            session_id=session_id,
            new_message=approval_response(request["approval_id"], approve),
            invocation_id=request["invocation_id"],
        )
    ]
    return paused, request, resumed


@pytest.mark.parametrize(
    "approve,expected_status,expected_suffix",
    [(True, "approved", "HUMAN"), (False, "rejected", None)],
)
def test_large_order_pause_resume(approve, expected_status, expected_suffix):
    paused, request, resumed = asyncio.run(_drive(_stub_runner(), approve))

    # The pause surfaced an adk_request_confirmation call carrying both ids.
    confirmation_calls = [
        part.function_call.name
        for event in paused
        if event.content
        for part in (event.content.parts or [])
        if getattr(part, "function_call", None)
    ]
    assert CONFIRMATION_FUNCTION in confirmation_calls
    assert request is not None
    assert request["approval_id"]
    assert request["invocation_id"]

    # Resume rejoined the same paused invocation (invocation_id round-trip).
    assert resumed
    assert all(e.invocation_id == request["invocation_id"] for e in resumed)

    # The resumed tool re-ran with the confirmation and produced the real status
    # (approval_id round-trip: a wrong id leaves the tool un-re-executed).
    response = _order_response([e.content for e in resumed if e.content])
    assert response is not None
    assert response["status"] == expected_status
    if expected_suffix:
        assert response["order_id"].endswith(expected_suffix)


@pytest.mark.parametrize("approve,expected", [(True, "approved"), (False, "rejected")])
def test_run_order_resumes_through_real_runner(approve, expected):
    runner = _stub_runner()
    result = asyncio.run(run_order(runner, ORDER, approve=approve, app_name=APP_NAME))
    assert expected in result
