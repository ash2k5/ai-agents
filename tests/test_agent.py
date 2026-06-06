"""Tests that the agent and app are wired correctly, without any live call."""

from ai_agents.agent import TOOLS, build_root_agent, root_agent
from ai_agents.app import APP_NAME, app, build_runner


def test_tools_wired():
    names = {fn.__name__ for fn in TOOLS}
    assert names == {
        "get_product_info",
        "get_fee_for_payment_method",
        "get_exchange_rate",
        "save_userinfo",
        "retrieve_userinfo",
        "place_shipping_order",
    }


def test_root_agent_identity():
    assert root_agent.name == "commerce_assistant"
    assert len(root_agent.tools) == len(TOOLS)


def test_instruction_mentions_approval():
    assert "approval" in root_agent.instruction.lower()


def test_build_root_agent_is_fresh():
    assert build_root_agent() is not root_agent


def test_app_is_resumable():
    assert app.name == APP_NAME
    assert app.resumability_config.is_resumable is True


def test_build_runner_with_injected_service():
    from google.adk.sessions import InMemorySessionService

    runner = build_runner(InMemorySessionService())
    assert runner is not None
