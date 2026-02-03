"""NDF (Non-Deliverable Forward) product handler."""

from typing import Any

from fxfixparser.core.message import FixMessage
from fxfixparser.products.base import ProductHandler


class NDFHandler(ProductHandler):
    """Handler for FX NDF trades."""

    @property
    def product_type(self) -> str:
        return "NDF"

    def detect(self, message: FixMessage) -> bool:
        """Detect if this is an NDF trade.

        NDF is identified by:
        - SecurityType (167) = FXNDF
        - Or presence of NDF-specific tags (fixing date, fixing source)
        """
        security_type = message.get_value(167)
        if security_type and security_type.upper() == "FXNDF":
            return True

        # Check for NDF-specific custom tags
        if message.get_value(5709) or message.get_value(5711):
            return True

        return False

    def extract_details(self, message: FixMessage) -> dict[str, Any]:
        details = super().extract_details(message)
        details["settlement_date"] = message.get_value(64)
        details["fixing_date"] = message.get_value(5709)
        details["fixing_rate"] = message.get_value(5710)
        details["fixing_source"] = message.get_value(5711)
        details["settlement_currency"] = message.get_value(120)
        return details
