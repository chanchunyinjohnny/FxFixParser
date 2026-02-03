"""Swap product handler."""

from typing import Any

from fxfixparser.core.message import FixMessage
from fxfixparser.products.base import ProductHandler


class SwapHandler(ProductHandler):
    """Handler for FX Swap trades."""

    @property
    def product_type(self) -> str:
        return "Swap"

    def detect(self, message: FixMessage) -> bool:
        """Detect if this is a swap trade.

        Swap is identified by:
        - SecurityType (167) = FXSWAP
        - Or OrdType (40) = G (ForexSwap)
        - Or presence of both SettlDate (64) and SettlDate2 (193)
        - Or presence of FarLegSettlType (8004) - Smart Trade specific
        - Or presence of both SettlType (63) and OrderQty2 (192) indicating two legs
        """
        security_type = message.get_value(167)
        if security_type and security_type.upper() == "FXSWAP":
            return True

        ord_type = message.get_value(40)
        if ord_type == "G":
            return True

        # Check for two settlement dates (near and far legs)
        if message.get_value(64) and message.get_value(193):
            return True

        # Check for FarLegSettlType (8004) - Smart Trade specific swap indicator
        if message.get_value(8004):
            return True

        # Check for near leg SettlType and far leg quantity (indicates swap)
        if message.get_value(63) and message.get_value(192):
            return True

        return False

    def extract_details(self, message: FixMessage) -> dict[str, Any]:
        details = super().extract_details(message)
        details["near_settlement_date"] = message.get_value(64)
        details["far_settlement_date"] = message.get_value(193)
        details["near_quantity"] = message.get_value(32)
        details["far_quantity"] = message.get_value(192)
        details["spot_rate"] = message.get_value(194)
        details["forward_points"] = message.get_value(195)
        return details
