"""The commerce assistant agent.

Exposes ``root_agent`` so the package is discoverable by ``adk web`` and ``adk run``.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from .config import build_model
from .tools import (
    get_exchange_rate,
    get_fee_for_payment_method,
    get_product_info,
    place_shipping_order,
    retrieve_userinfo,
    save_userinfo,
)

INSTRUCTION = """You are a commerce assistant for an online electronics vendor.

You can help customers with:
- Product information: use get_product_info for price, stock, and specifications.
- Payment fees: use get_fee_for_payment_method to quote the fee for a payment method.
- Currency conversion: use get_exchange_rate to convert a price between currencies.
- Shipping orders: use place_shipping_order with the container count and destination.

When a customer introduces themselves, call save_userinfo to store their name and country,
and retrieve_userinfo to recall it later in the conversation.

Shipping orders above the large-order threshold require human approval. When an order is
pending approval, tell the customer it is awaiting approval and wait. Once a decision
arrives, summarize the final status, the order id, the container count, and the destination.

Be concise and professional. If a lookup fails, say so plainly and suggest a valid option.
"""

TOOLS = [
    get_product_info,
    get_fee_for_payment_method,
    get_exchange_rate,
    save_userinfo,
    retrieve_userinfo,
    place_shipping_order,
]


def build_root_agent() -> LlmAgent:
    return LlmAgent(
        name="commerce_assistant",
        model=build_model(),
        description="Assists customers with products, fees, currency conversion, and shipping.",
        instruction=INSTRUCTION,
        tools=list(TOOLS),
    )


root_agent = build_root_agent()
