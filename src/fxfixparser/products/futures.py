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
        - SecurityType (167) = FUT, or
        - MaturityMonthYear (200) + SecurityExchange (207) both present, or
        - MarketSegmentID (1300) = FX with a SecurityID (48) (SGX style)
        """
        security_type = message.get_value(167)
        if security_type and security_type.upper() == "FUT":
            return True

        if message.get_value(200) and message.get_value(207):
            return True

        if (
            message.venue == "SGX Titan OTC"
            and message.get_value(1300) == "FX"
            and message.get_value(48)
        ):
            return True

        return False

    def extract_details(self, message: FixMessage) -> dict[str, Any]:
        details = super().extract_details(message)
        details["maturity_month_year"] = message.get_value(200)
        details["maturity_date"] = message.get_value(541)
        details["security_exchange"] = message.get_value(207)
        details["contract_multiplier"] = message.get_value(231)
        details["product_code"] = message.get_value(48)
        # Prefer the venue-supplied canonical name (e.g. SGX enrichment),
        # then ProductComplex (1227), then SecurityDesc (107).
        details["product_name"] = (
            message.venue_extras.get("product_name")
            or message.get_value(1227)
            or message.get_value(107)
        )
        return details
