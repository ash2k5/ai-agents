"""Human-in-the-loop approval helpers for the resumable shipping workflow.

``find_approval_request`` and ``approval_response`` are pure and unit-tested.
``run_order`` drives a runner through the pause/resume cycle and is exercised by
``examples/approval_agent.py`` against a live model.
"""

from __future__ import annotations

import uuid

from google.genai import types

CONFIRMATION_FUNCTION = "adk_request_confirmation"


def find_approval_request(events) -> dict | None:
    """Returns the approval and invocation ids if events contain a confirmation request."""
    for event in events:
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            call = getattr(part, "function_call", None)
            if call and call.name == CONFIRMATION_FUNCTION:
                return {"approval_id": call.id, "invocation_id": event.invocation_id}
    return None


def approval_response(approval_id: str, approved: bool) -> types.Content:
    """Builds the function-response content that resumes a paused order."""
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=approval_id,
                    name=CONFIRMATION_FUNCTION,
                    response={"confirmed": approved},
                )
            )
        ],
    )


def final_text(events) -> str:
    """Joins every text part across all events, intermediate (non-final) text included.

    Unlike the examples, this does not filter on ``is_final_response()``: the driver wants
    the full transcript, so mid-stream narration is part of the returned text by design.
    """
    texts = [
        part.text
        for event in events
        if event.content and event.content.parts
        for part in event.content.parts
        if getattr(part, "text", None)
    ]
    return "\n".join(texts).strip()


async def run_order(
    runner, query: str, *, approve: bool, app_name: str, user_id: str = "user"
) -> str:
    """Runs a shipping request end to end, supplying the approval decision if asked."""
    session_id = f"order-{uuid.uuid4().hex[:8]}"
    await runner.session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    message = types.Content(role="user", parts=[types.Part(text=query)])
    events = [
        event
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        )
    ]

    request = find_approval_request(events)
    if request is None:
        return final_text(events)

    resumed = [
        event
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=approval_response(request["approval_id"], approve),
            invocation_id=request["invocation_id"],
        )
    ]
    return final_text(resumed)
