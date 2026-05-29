"""SGX Titan OTC venue handler.

Supports the SGX Titan OTC FIX 5.0 SP2 / FIXT 1.1 gateway used for
off-market trade reporting of SGX listed derivatives, including SGX FX
futures (KRW/USD, USD/CNH, USD/SGD, FlexC variants, etc.).

Custom tag definitions and the FX product-code table are scoped to this
module; the parser overlays venue custom tags on top of the base
dictionary at parse time (see core/parser.py::_get_dictionary_for_venue).
"""

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.core.message import FixMessage, ParsedTrade
from fxfixparser.venues.base import VenueHandler

# SGX FX futures product code -> human-readable name. Codes are the value
# of tag 48 (SecurityID) when 22=M (Marketplace-assigned) and 1300=FX.
_SGX_FX_PRODUCT_CODES: dict[str, str] = {
    "US": "USD/SGD FX Futures",
    "AU": "AUD/USD FX Futures",
    "AJ": "AUD/JPY FX Futures",
    "IU": "INR/USD FX Futures",
    "KU": "KRW/USD FX Futures",
    "KJ": "KRW/JPY FX Futures",
    "CY": "CNY/USD FX Futures",
    "UC": "USD/CNH FX Futures",
    "UJ": "USD/JPY FX Futures (Titan)",
    "UY": "USD/JPY FX Futures (Standard)",
    "TU": "THB/USD FX Futures",
    "TD": "TWD/USD FX Futures",
    "SY": "SGD/CNH FX Futures",
    "YS": "CNY/SGD FX Futures",
    "EC": "EUR/CNH FX Futures",
    "IDR": "IDR/USD FX Futures",
    "PHP": "PHP/USD FX Futures",
    "MYR": "MYR/USD FX Futures",
    "MYS": "MYR/SGD FX Futures",
    # FlexC variants
    "IUTM": "INR/USD FlexC FX Futures",
    "KUTM": "KRW/USD FlexC FX Futures",
    "USTM": "USD/SGD FlexC FX Futures",
    "TDTM": "TWD/USD FlexC FX Futures",
    "UCTM": "USD/CNH FlexC FX Futures",
}


def sgx_product_name(security_id: str | None) -> str | None:
    """Return the canonical SGX FX futures product name for a SecurityID.

    Returns None for unknown codes, empty strings or None.
    """
    if not security_id:
        return None
    return _SGX_FX_PRODUCT_CODES.get(security_id)


# Custom tag definitions added in Task 3.
_SGX_CUSTOM_TAGS: dict[int, FixFieldDefinition] = {
    1300: FixFieldDefinition(
        tag=1300,
        name="MarketSegmentID",
        field_type="STRING",
        description="SGX asset class indicator for the product.",
        valid_values={
            "FX": "FX asset class",
            "EQ": "Equity",
            "CO": "Commodity",
            "IR": "Interest Rate",
        },
    ),
    1227: FixFieldDefinition(
        tag=1227,
        name="ProductComplex",
        field_type="STRING",
        description=("Full human-readable product name " "(e.g. 'SGX KRW/USD FLEX FX FUTURES')."),
    ),
    1151: FixFieldDefinition(
        tag=1151,
        name="SecurityGroup",
        field_type="STRING",
        description="SGX product group code.",
    ),
    1306: FixFieldDefinition(
        tag=1306,
        name="PriceLimitType",
        field_type="INT",
        description="Type of daily price limit applied.",
        valid_values={
            "0": "No limit",
            "1": "Hard limit",
            "2": "Soft limit",
        },
    ),
    1148: FixFieldDefinition(
        tag=1148,
        name="LowLimitPrice",
        field_type="PRICE",
        description="Daily low price limit.",
    ),
    1149: FixFieldDefinition(
        tag=1149,
        name="HighLimitPrice",
        field_type="PRICE",
        description="Daily high price limit.",
    ),
    1150: FixFieldDefinition(
        tag=1150,
        name="TradingReferencePrice",
        field_type="PRICE",
        description="Trading reference price.",
    ),
    1057: FixFieldDefinition(
        tag=1057,
        name="AggressorIndicator",
        field_type="BOOLEAN",
        description="Whether the order was the aggressor side of the trade.",
    ),
    1003: FixFieldDefinition(
        tag=1003,
        name="TradeID",
        field_type="STRING",
        description="Titan OTC internal trade identifier.",
    ),
    1005: FixFieldDefinition(
        tag=1005,
        name="SideTradeReportID",
        field_type="STRING",
        description="Client system internal unique trade report identifier.",
    ),
    1139: FixFieldDefinition(
        tag=1139,
        name="ExchangeSpecialInstructions",
        field_type="STRING",
        description="Trade report special instructions.",
    ),
    1310: FixFieldDefinition(
        tag=1310,
        name="NoMarketSegments",
        field_type="NUMINGROUP",
        description="Count of market segments in the repeating group.",
    ),
    2343: FixFieldDefinition(
        tag=2343,
        name="RiskLimitCheckStatus",
        field_type="INT",
        description="Result of the risk limit check.",
        valid_values={
            "0": "Accepted",
            "1": "Rejected",
            "2": "Pending",
            "3": "Risk Engine Unavailable",
        },
    ),
    2344: FixFieldDefinition(
        tag=2344,
        name="SideRiskLimitCheckStatus",
        field_type="INT",
        description="Side-level result of the risk limit check.",
        valid_values={
            "0": "Accepted",
            "1": "Rejected",
            "2": "Pending",
            "3": "Risk Engine Unavailable",
        },
    ),
    1461: FixFieldDefinition(
        tag=1461,
        name="NoTargetPartyIDs",
        field_type="NUMINGROUP",
        description="Count of target party identifiers.",
    ),
    1462: FixFieldDefinition(
        tag=1462,
        name="TargetPartyID",
        field_type="STRING",
        description="Target party identifier / code.",
    ),
    1463: FixFieldDefinition(
        tag=1463,
        name="TargetPartyIDSource",
        field_type="CHAR",
        description="Source of the target party identifier.",
        valid_values={"D": "Proprietary / Custom Code"},
    ),
    1464: FixFieldDefinition(
        tag=1464,
        name="TargetPartyRole",
        field_type="INT",
        description="Role of the target party.",
    ),
    1625: FixFieldDefinition(
        tag=1625,
        name="MatchInst",
        field_type="INT",
        description="Match instruction for trade confirmation.",
        valid_values={"1": "Match (confirm)", "2": "Reject"},
    ),
    1626: FixFieldDefinition(
        tag=1626,
        name="MatchAttribTagID",
        field_type="STRING",
        description="Match attribute tag identifier.",
    ),
    1627: FixFieldDefinition(
        tag=1627,
        name="MatchAttribValue",
        field_type="STRING",
        description="Match attribute value.",
    ),
    1418: FixFieldDefinition(
        tag=1418,
        name="LegLastQty",
        field_type="QTY",
        description="Quantity bought/sold for this leg of a multi-leg trade.",
    ),
    1427: FixFieldDefinition(
        tag=1427,
        name="SideExecID",
        field_type="STRING",
        description="Side-level execution identifier.",
    ),
    552: FixFieldDefinition(
        tag=552,
        name="NoSides",
        field_type="NUMINGROUP",
        description="Count of sides in the repeating group.",
    ),
}


class SGXTitanOTCHandler(VenueHandler):
    """Handler for SGX Titan OTC FIX messages."""

    @property
    def name(self) -> str:
        return "SGX Titan OTC"

    @property
    def sender_comp_ids(self) -> list[str]:
        # TITANOTC is the venue-side CompID confirmed from PDF samples.
        # The others cover common alternative spellings firms have used.
        return [
            "TITANOTC",
            "SGX-OTC",
            "SGXTITAN",
            "SGX_TITAN_OTC",
        ]

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        return list(_SGX_CUSTOM_TAGS.values())

    def enhance_message(self, message: FixMessage) -> FixMessage:
        message = super().enhance_message(message)
        if message.get_value(1300) == "FX":
            sec_id = message.get_value(48)
            name = sgx_product_name(sec_id)
            if name:
                message.venue_extras["product_name"] = name
        return message

    def extract_trade(self, message: FixMessage) -> ParsedTrade:
        trade = super().extract_trade(message)
        trade.order_id = trade.order_id or message.get_value(571)
        trade.exec_id = trade.exec_id or message.get_value(1003) or message.get_value(1005)
        return trade
