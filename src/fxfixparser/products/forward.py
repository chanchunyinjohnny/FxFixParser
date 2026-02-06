"""Forward product handler."""

import re
from typing import Any

from fxfixparser.core.message import FixMessage
from fxfixparser.products.base import ProductHandler


# Settlement type values that indicate spot (not forward)
SPOT_SETTL_TYPES = {
    "0", "1", "2", "3", "C",  # Regular, Cash, NextDay, TPlus2, FXSpot
    "SPOT", "TOD", "TOM", "ONI", "SNX", "TNX",  # Spot tenors
}

# Pattern for forward tenor codes: W1-W3, M1-M21, Y1-Y30, D2-D4,
# IMM months, month-end codes
FORWARD_TENOR_PATTERN = re.compile(
    r"^(W[1-3]|M[1-9]\d?|Y[1-9]\d?|D[2-4]|"
    r"JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|"
    r"ME[1-9]\d?)$",
    re.IGNORECASE,
)


class ForwardHandler(ProductHandler):
    """Handler for FX Forward trades."""

    @property
    def product_type(self) -> str:
        return "Forward"

    def detect(self, message: FixMessage) -> bool:
        """Detect if this is a forward trade.

        Forward is identified by:
        - SecurityType (167) = FXFWD
        - SettlType (63) = 6 (Future) or B (BrokenDate)
        - SettlType (63) is a forward tenor code (e.g. M1, W2, Y1)
        - Or presence of forward points (tag 195)
        """
        security_type = message.get_value(167)
        if security_type and security_type.upper() == "FXFWD":
            return True

        settl_type = message.get_value(63)
        if settl_type in ("6", "B"):
            return True

        # Check for forward tenor codes (e.g. M1, W2, Y1, IMM dates)
        if settl_type and FORWARD_TENOR_PATTERN.match(settl_type):
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
