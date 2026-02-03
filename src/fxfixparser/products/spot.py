"""Spot product handler."""

from typing import Any

from fxfixparser.core.message import FixMessage
from fxfixparser.products.base import ProductHandler


class SpotHandler(ProductHandler):
    """Handler for FX Spot trades."""

    @property
    def product_type(self) -> str:
        return "Spot"

    # Message types that are trade-related (can have a product type)
    TRADE_MSG_TYPES = {
        "8",   # ExecutionReport
        "D",   # NewOrderSingle
        "E",   # NewOrderList
        "F",   # OrderCancelRequest
        "G",   # OrderCancelReplaceRequest
        "R",   # QuoteRequest
        "S",   # Quote
        "i",   # MassQuote
        "W",   # MarketDataSnapshotFullRefresh
        "X",   # MarketDataIncrementalRefresh
        "AE",  # TradeCaptureReport
        "AR",  # TradeCaptureReportRequest
    }

    def detect(self, message: FixMessage) -> bool:
        """Detect if this is a spot trade.

        Spot is identified by:
        - SettlType (63) = 0 (Regular), 1 (Cash), or C (FXSpot)
        - Or SecurityType (167) = FXSPOT
        - Or settlement date is T+2 or less

        Returns False for non-trade messages (Heartbeat, Logon, etc.)
        """
        # Only detect product type for trade-related messages
        msg_type = message.msg_type
        if msg_type not in self.TRADE_MSG_TYPES:
            return False

        security_type = message.get_value(167)
        if security_type and security_type.upper() in ("FXSPOT", "FX"):
            return True

        settl_type = message.get_value(63)
        if settl_type in ("0", "1", "2", "3", "C"):
            return True

        # Default to spot for trade messages if no other product type matches
        return True

    def extract_details(self, message: FixMessage) -> dict[str, Any]:
        details = super().extract_details(message)
        details["settlement_date"] = message.get_value(64)
        details["spot_rate"] = message.get_value(194)
        return details
