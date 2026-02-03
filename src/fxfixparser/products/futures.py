"""Futures product handler."""

from typing import Any

from fxfixparser.core.message import FixMessage
from fxfixparser.products.base import ProductHandler


class FuturesHandler(ProductHandler):
    """Handler for FX Futures trades."""

    @property
    def product_type(self) -> str:
        return "Futures"

    def detect(self, message: FixMessage) -> bool:
        """Detect if this is a futures trade.

        Futures is identified by:
        - SecurityType (167) = FUT
        - Or presence of MaturityMonthYear (200) with exchange
        - Or presence of SecurityExchange (207) with FX symbol
        """
        security_type = message.get_value(167)
        if security_type and security_type.upper() == "FUT":
            return True

        # Check for maturity month/year with exchange
        if message.get_value(200) and message.get_value(207):
            return True

        return False

    def extract_details(self, message: FixMessage) -> dict[str, Any]:
        details = super().extract_details(message)
        details["maturity_month_year"] = message.get_value(200)
        details["maturity_date"] = message.get_value(541)
        details["security_exchange"] = message.get_value(207)
        details["contract_multiplier"] = message.get_value(231)
        return details
