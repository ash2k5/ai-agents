"""Runnable demo of the human-in-the-loop shipping approval workflow.

Sends three orders through the resumable app: a small order that auto-approves, a large
order a human approves, and a large order a human rejects. Requires GOOGLE_API_KEY.

    python examples/approval_agent.py
"""

from __future__ import annotations

import asyncio

from google.adk.sessions import InMemorySessionService

from ai_agents.app import APP_NAME, build_runner
from ai_agents.approval import run_order
from ai_agents.config import require_api_key

SCENARIOS = [
    ("Ship 3 containers to Singapore", True),
    ("Ship 10 containers to Rotterdam", True),
    ("Ship 8 containers to Los Angeles", False),
]


async def main() -> None:
    require_api_key()
    runner = build_runner(InMemorySessionService())
    for query, approve in SCENARIOS:
        decision = "approve" if approve else "reject"
        print(f"\n> {query}  (human will {decision})")
        result = await run_order(runner, query, approve=approve, app_name=APP_NAME)
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
