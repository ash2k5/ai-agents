"""Runnable demo of Model Context Protocol (MCP) tool integration.

Wires the MCP "everything" reference server (started on demand via npx) and asks the agent
to call its getTinyImage tool. Requires GOOGLE_API_KEY and Node.js/npx on PATH.

    python examples/mcp_agent.py
"""

from __future__ import annotations

import asyncio

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from ai_agents.config import build_model, require_api_key

try:
    from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
    from mcp import StdioServerParameters
except ImportError as exc:
    raise SystemExit(
        'This example needs the "mcp" extra. Install it with:\n'
        '    uv pip install -e ".[mcp]"'
    ) from exc

APP_NAME = "mcp_demo"
USER_ID = "demo_user"
SESSION_ID = "mcp-session"


def build_agent() -> LlmAgent:
    image_server = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-everything"],
            ),
            timeout=30,
        ),
        tool_filter=["getTinyImage"],
    )
    return LlmAgent(
        name="mcp_image_agent",
        model=build_model(),
        instruction="Use the MCP getTinyImage tool to generate an image when asked.",
        tools=[image_server],
    )


async def main() -> None:
    require_api_key()
    runner = InMemoryRunner(agent=build_agent(), app_name=APP_NAME)
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    message = types.Content(
        role="user", parts=[types.Part(text="Generate a tiny test image.")]
    )
    async for event in runner.run_async(
        user_id=USER_ID, session_id=SESSION_ID, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)


if __name__ == "__main__":
    asyncio.run(main())
