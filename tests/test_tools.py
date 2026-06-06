"""Unit tests for the function tools: happy paths plus edge and failure cases."""

from ai_agents.config import LARGE_ORDER_THRESHOLD
from ai_agents.tools import (
    get_exchange_rate,
    get_fee_for_payment_method,
    get_product_info,
    place_shipping_order,
    retrieve_userinfo,
    save_userinfo,
)


class TestGetProductInfo:
    def test_known_product(self):
        assert "iPhone 15 Pro" in get_product_info("iPhone 15 Pro")

    def test_case_and_whitespace_insensitive(self):
        assert "iPhone 15 Pro" in get_product_info("  iPHONE 15 pro  ")

    def test_unknown_product_lists_alternatives(self):
        result = get_product_info("Nokia 3310")
        assert "don't have information" in result
        assert "Available products" in result

    def test_empty_string(self):
        assert "Available products" in get_product_info("")


class TestGetFee:
    def test_known_method(self):
        result = get_fee_for_payment_method("Platinum Credit Card")
        assert result == {"status": "success", "fee_percentage": 0.02}

    def test_unknown_method(self):
        result = get_fee_for_payment_method("cash")
        assert result["status"] == "error"
        assert "cash" in result["error_message"]

    def test_whitespace_trimmed(self):
        assert get_fee_for_payment_method("  bank transfer ")["status"] == "success"


class TestGetExchangeRate:
    def test_known_pair(self):
        assert get_exchange_rate("USD", "EUR") == {"status": "success", "rate": 0.93}

    def test_case_insensitive(self):
        assert get_exchange_rate("usd", "jpy")["rate"] == 157.50

    def test_unknown_target(self):
        assert get_exchange_rate("USD", "GBP")["status"] == "error"

    def test_unknown_base(self):
        result = get_exchange_rate("XYZ", "EUR")
        assert result["status"] == "error"
        assert "XYZ/EUR" in result["error_message"]


class TestUserInfo:
    def test_save_then_retrieve(self, make_ctx):
        ctx = make_ctx()
        assert save_userinfo(ctx, "Sam", "Poland") == {"status": "success"}
        assert ctx.state["user:name"] == "Sam"
        assert retrieve_userinfo(ctx) == {
            "status": "success",
            "user_name": "Sam",
            "country": "Poland",
        }

    def test_save_trims_whitespace(self, make_ctx):
        ctx = make_ctx()
        save_userinfo(ctx, "  Sam  ", "  Poland ")
        assert ctx.state["user:name"] == "Sam"
        assert ctx.state["user:country"] == "Poland"

    def test_save_rejects_blank(self, make_ctx):
        ctx = make_ctx()
        assert save_userinfo(ctx, "  ", "Poland")["status"] == "error"
        assert "user:name" not in ctx.state

    def test_retrieve_without_data(self, make_ctx):
        assert retrieve_userinfo(make_ctx())["status"] == "error"

    def test_retrieve_partial_data(self, make_ctx):
        ctx = make_ctx(state={"user:name": "Sam"})
        assert retrieve_userinfo(ctx)["status"] == "error"


class TestPlaceShippingOrder:
    def test_small_order_auto_approved(self, make_ctx):
        result = place_shipping_order(3, "Singapore", make_ctx())
        assert result["status"] == "approved"
        assert result["order_id"].endswith("AUTO")

    def test_threshold_is_inclusive(self, make_ctx):
        result = place_shipping_order(LARGE_ORDER_THRESHOLD, "Singapore", make_ctx())
        assert result["status"] == "approved"

    def test_large_order_requests_confirmation(self, make_ctx):
        ctx = make_ctx()
        result = place_shipping_order(LARGE_ORDER_THRESHOLD + 1, "Rotterdam", ctx)
        assert result["status"] == "pending"
        assert ctx.requested is not None
        assert ctx.requested["payload"]["num_containers"] == LARGE_ORDER_THRESHOLD + 1

    def test_large_order_approved(self, make_ctx, confirmation):
        ctx = make_ctx(tool_confirmation=confirmation(True))
        result = place_shipping_order(10, "Rotterdam", ctx)
        assert result["status"] == "approved"
        assert result["order_id"].endswith("HUMAN")

    def test_large_order_rejected(self, make_ctx, confirmation):
        ctx = make_ctx(tool_confirmation=confirmation(False))
        result = place_shipping_order(10, "Rotterdam", ctx)
        assert result["status"] == "rejected"
