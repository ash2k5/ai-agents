"""Runnable demo of cross-session memory.

The agent stores a fact in one session; that session is written to the memory service; a
second, separate session recalls the fact via the load_memory tool. Requires GOOGLE_API_KEY.

    python examples/memory_agent.py
"""

from __future__ import annotations

import asyncio

from google.adk.agents import LlmAgent
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import load_memory
from google.genai import types

from ai_agents.config import build_model, require_api_key

APP_NAME = "memory_demo"
USER_ID = "demo_user"


def build_agent() -> LlmAgent:
    return LlmAgent(
        name="memory_assistant",
        model=build_model(),
        instruction=(
            "You are a helpful assistant with long-term memory. When the user asks about "
            "something they mentioned before, use the load_memory tool to search past "
            "conversations before answering."
        ),
        tools=[load_memory],
    )


async def turn(runner, memory_service, session_id, text, *, remember):
    sessions = runner.session_service
    await sessions.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    message = types.Content(role="user", parts=[types.Part(text=text)])
    print(f"\n[{session_id}] user  > {text}")
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=message
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    print(f"[{session_id}] agent > {part.text}")
    if remember:
        session = await sessions.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        await memory_service.add_session_to_memory(session)


async def main() -> None:
    require_api_key()
    memory_service = InMemoryMemoryService()
    runner = Runner(
        agent=build_agent(),
        app_name=APP_NAME,
        session_service=InMemorySessionService(),
        memory_service=memory_service,
    )
    await turn(
        runner,
        memory_service,
        "session-1",
        "My favorite color is teal. Please remember that.",
        remember=True,
    )
    await turn(
        runner,
        memory_service,
        "session-2",
        "What is my favorite color?",
        remember=False,
    )


if __name__ == "__main__":
    asyncio.run(main())
