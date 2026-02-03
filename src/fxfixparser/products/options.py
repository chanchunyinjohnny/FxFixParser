"""Options product handler."""

from typing import Any

from fxfixparser.core.message import FixMessage
from fxfixparser.products.base import ProductHandler


class OptionsHandler(ProductHandler):
    """Handler for FX Options trades."""

    @property
    def product_type(self) -> str:
        return "Options"

    def detect(self, message: FixMessage) -> bool:
        """Detect if this is an options trade.

        Options is identified by:
        - SecurityType (167) = OPT
        - Or presence of PutOrCall (201)
        - Or presence of StrikePrice (202)
        """
        security_type = message.get_value(167)
        if security_type and security_type.upper() == "OPT":
            return True

        # Check for options-specific fields
        if message.get_value(201) or message.get_value(202):
            return True

        return False

    def extract_details(self, message: FixMessage) -> dict[str, Any]:
        details = super().extract_details(message)

        put_or_call = message.get_field(201)
        if put_or_call:
            details["put_or_call"] = put_or_call.value_description or put_or_call.raw_value

        details["strike_price"] = message.get_value(202)
        details["maturity_date"] = message.get_value(541)
        details["maturity_month_year"] = message.get_value(200)
        details["opt_attribute"] = message.get_value(206)
        return details
