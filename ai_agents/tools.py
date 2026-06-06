"""Function tools for the commerce assistant.

Each tool is a pure, side-effect-free lookup over in-memory sample data, returning a
structured ``{"status": ...}`` dict (or a string for the catalog) so the model can branch
on success and error. The docstrings and type hints are functional: ADK turns them into
the function-calling schema the model sees, so they are kept deliberately descriptive.
"""

from __future__ import annotations

from typing import Any

from google.adk.tools import ToolContext

from .config import LARGE_ORDER_THRESHOLD

_FEE_TABLE = {
    "platinum credit card": 0.02,
    "gold debit card": 0.035,
    "bank transfer": 0.01,
}

_RATE_TABLE: dict[str, dict[str, float]] = {
    "usd": {"eur": 0.93, "jpy": 157.50, "inr": 83.58},
}

_PRODUCT_CATALOG = {
    "iphone 15 pro": "iPhone 15 Pro, $999, Low Stock (8 units), 128GB, Titanium finish",
    "samsung galaxy s24": "Samsung Galaxy S24, $799, In Stock (31 units), 256GB, Phantom Black",
    "dell xps 15": 'Dell XPS 15, $1,299, In Stock (45 units), 15.6" display, 16GB RAM, 512GB SSD',
    "macbook pro 14": 'MacBook Pro 14", $1,999, In Stock (22 units), M3 Pro chip, 18GB RAM, 512GB SSD',
    "sony wh-1000xm5": "Sony WH-1000XM5 Headphones, $399, In Stock (67 units), Noise-canceling, 30hr battery",
    "ipad air": 'iPad Air, $599, In Stock (28 units), 10.9" display, 64GB',
    "lg ultrawide 34": 'LG UltraWide 34" Monitor, $499, Out of Stock, Expected: Next week',
}


def get_product_info(product_name: str) -> str:
    """Looks up price, availability, and specifications for a product.

    Args:
        product_name: Product name, for example "iPhone 15 Pro" or "MacBook Pro 14".

    Returns:
        A description string, or a message listing the available products when there is
        no match.
    """
    key = product_name.lower().strip()
    if key in _PRODUCT_CATALOG:
        return f"Product: {_PRODUCT_CATALOG[key]}"
    available = ", ".join(name.title() for name in _PRODUCT_CATALOG)
    return f"Sorry, I don't have information for {product_name}. Available products: {available}"


def get_fee_for_payment_method(method: str) -> dict:
    """Looks up the transaction fee fraction for a payment method.

    Args:
        method: Payment method name, for example "platinum credit card" or "bank transfer".

    Returns:
        On success ``{"status": "success", "fee_percentage": 0.02}``; otherwise
        ``{"status": "error", "error_message": ...}``.
    """
    fee = _FEE_TABLE.get(method.lower().strip())
    if fee is None:
        return {
            "status": "error",
            "error_message": f"Payment method '{method}' not found",
        }
    return {"status": "success", "fee_percentage": fee}


def get_exchange_rate(base_currency: str, target_currency: str) -> dict:
    """Looks up the exchange rate between two ISO 4217 currencies.

    Args:
        base_currency: Currency to convert from, for example "USD".
        target_currency: Currency to convert to, for example "EUR".

    Returns:
        On success ``{"status": "success", "rate": 0.93}``; otherwise
        ``{"status": "error", "error_message": ...}``.
    """
    base = base_currency.lower().strip()
    target = target_currency.lower().strip()
    rate = _RATE_TABLE.get(base, {}).get(target)
    if rate is None:
        return {
            "status": "error",
            "error_message": f"Unsupported currency pair: {base_currency}/{target_currency}",
        }
    return {"status": "success", "rate": rate}


def save_userinfo(
    tool_context: ToolContext, user_name: str, country: str
) -> dict[str, Any]:
    """Records the user's name and country in session state for later recall.

    Args:
        tool_context: ADK-provided context giving access to session state.
        user_name: The user's name.
        country: The user's country.

    Returns:
        ``{"status": "success"}`` on success, otherwise an error dict.
    """
    name = user_name.strip()
    place = country.strip()
    if not name or not place:
        return {
            "status": "error",
            "error_message": "Both user_name and country are required",
        }
    tool_context.state["user:name"] = name
    tool_context.state["user:country"] = place
    return {"status": "success"}


def retrieve_userinfo(tool_context: ToolContext) -> dict[str, Any]:
    """Retrieves the user's saved name and country from session state.

    Args:
        tool_context: ADK-provided context giving access to session state.

    Returns:
        ``{"status": "success", "user_name": ..., "country": ...}`` when present,
        otherwise ``{"status": "error", "message": "No user info found"}``.
    """
    user_name = tool_context.state.get("user:name")
    country = tool_context.state.get("user:country")
    if user_name and country:
        return {"status": "success", "user_name": user_name, "country": country}
    return {"status": "error", "message": "No user info found in session state"}


def place_shipping_order(
    num_containers: int, destination: str, tool_context: ToolContext
) -> dict:
    """Places a shipping order; orders above the large-order threshold need human approval.

    Orders of ``LARGE_ORDER_THRESHOLD`` containers or fewer are auto-approved. Larger
    orders pause for confirmation: the first call requests approval and returns a pending
    status; ADK calls the tool again once a human decision arrives.

    Args:
        num_containers: Number of containers to ship.
        destination: Shipping destination.
        tool_context: ADK-provided context used to request and read approval.

    Returns:
        A dict whose ``status`` is one of "approved", "pending", or "rejected".
    """
    if num_containers <= LARGE_ORDER_THRESHOLD:
        return {
            "status": "approved",
            "order_id": f"ORD-{num_containers}-AUTO",
            "num_containers": num_containers,
            "destination": destination,
            "message": f"Order auto-approved: {num_containers} containers to {destination}",
        }

    if not tool_context.tool_confirmation:
        tool_context.request_confirmation(
            hint=f"Large order: {num_containers} containers to {destination}. Approve?",
            payload={"num_containers": num_containers, "destination": destination},
        )
        return {
            "status": "pending",
            "message": f"Order for {num_containers} containers requires approval",
        }

    if tool_context.tool_confirmation.confirmed:
        return {
            "status": "approved",
            "order_id": f"ORD-{num_containers}-HUMAN",
            "num_containers": num_containers,
            "destination": destination,
            "message": f"Order approved: {num_containers} containers to {destination}",
        }
    return {
        "status": "rejected",
        "message": f"Order rejected: {num_containers} containers to {destination}",
    }
