"""Forward product handler."""

from typing import Any

from fxfixparser.core.message import FixMessage
from fxfixparser.products.base import ProductHandler


class ForwardHandler(ProductHandler):
    """Handler for FX Forward trades."""

    @property
    def product_type(self) -> str:
        return "Forward"

    def detect(self, message: FixMessage) -> bool:
        """Detect if this is a forward trade.

        Forward is identified by:
        - SettlType (63) = 6 (Future) or B (BrokenDate)
        - Or SecurityType (167) = FXFWD
        - Or presence of forward points (tag 195)
        """
        security_type = message.get_value(167)
        if security_type and security_type.upper() == "FXFWD":
            return True

        settl_type = message.get_value(63)
        if settl_type in ("6", "B"):
            return True

        # Check for forward points
        if message.get_value(195):
            return True

        return False

    def extract_details(self, message: FixMessage) -> dict[str, Any]:
        details = super().extract_details(message)
        details["settlement_date"] = message.get_value(64)
        details["spot_rate"] = message.get_value(194)
        details["forward_points"] = message.get_value(195)
        return details
