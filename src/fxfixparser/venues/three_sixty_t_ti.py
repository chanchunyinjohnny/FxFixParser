"""360T TradeImporter (TI) venue handler.

Supports the 360 Treasury Systems (Deutsche Boerse) **TradeImporter** FIX API
(v3.8) — a post-trade STP feed, distinct from the RFS Market Taker interface
(``three_sixty_t.py``). The two are modelled as sibling venues "360T TI" and
"360T RFS", mirroring the Bloomberg FXGO / DOR pair.

Characteristics of the TI API (FIX 4.4):

* the **only** business message is the ExecutionReport (35=8); it always carries
  ``OrdStatus(39)=2`` Filled / ``ExecType(150)=F`` Trade, ``LastShares(32)=0`` and
  ``CumQty(14)=0`` — so trade quantity is read from ``OrderQty(38)``, not 32;
* CompIDs use a ``_TI`` suffix (``360T_TI`` ↔ client ``*_TI``);
* ``ProductType(7071)`` carries the product directly (``FX-SPOT``, ``FX-FWD``,
  ``FX-SWAP``, ``MM`` …) — unlike RFS, which uses ``FX-STD``/``FX-BT`` and derives
  the product from field combinations;
* swap far-leg executed rate rides in ``LastPx2(6160)`` (near leg ``LastPx(31)``),
  far settle in ``SettlDate2(193)``, far qty in ``OrderQty2(192)``;
* competing-dealer quotes ride in the ``NoCompetingQuotes(9516)`` group;
* ``Side(54)`` is relative to the base currency (ccy1) and, for swaps, to the far
  leg — the same convention as RFS.

Only the **Core FX set** (Spot, Forward, NDF, Swap, NDS, FX Option, FX Time
Option) gets full Trade-Summary economic extraction; every other product (MM,
Commodities, Futures, EFP, Repo, …) still has all its tags decoded but uses the
generic summary.

Venue custom tags are defined in Python (no runtime XML), per the project's
proprietary-data policy. See docs/superpowers/specs/2026-06-06-360t-tradeimporter-support-design.md.
"""

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.core.fx_math import parse_symbol, pip_size, swap_side_actions
from fxfixparser.core.message import FixMessage, ParsedTrade
from fxfixparser.venues.base import VenueHandler


def _to_float(value: str | None) -> float | None:
    """Parse a tag value as float, returning None on missing / invalid."""
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _price(tag: int, name: str, desc: str) -> FixFieldDefinition:
    return FixFieldDefinition(tag, name, "PRICE", desc)


# Competing-quote group (9516) members. Every entry repeats CompetingQuoteDealer
# (9517); the remaining fields are optional per provider.
_COMPETING_QUOTE_TAGS: dict[int, FixFieldDefinition] = {
    9516: FixFieldDefinition(
        9516, "NoCompetingQuotes", "NUMINGROUP", "Number of competing quote providers."
    ),
    9517: FixFieldDefinition(
        9517, "CompetingQuoteDealer", "STRING", "Provider of a competitive quote."
    ),
    9518: _price(
        9518, "CompetingQuote", "Outright rate of the competitive provider (near leg for swaps)."
    ),
    9520: _price(
        9520, "CompetingQuoteLeg2", "Far-leg rate of the competitive provider (swaps/NDS)."
    ),
    9522: _price(
        9522, "CompetingQuoteSpotRate", "Reference spot rate of the competitive provider."
    ),
    9523: _price(9523, "CompetingQuoteMidSpotRate", "Mid spot rate of the competitive quote."),
    9524: _price(
        9524, "CompetingQuoteMidPx", "Mid price of the competitive quote (near leg for swaps)."
    ),
    9525: _price(
        9525, "CompetingQuoteMidPx2", "Mid price of the far leg of the competitive quote."
    ),
    9526: _price(
        9526,
        "CompetingQuoteProfitLoss",
        "Absolute difference vs the executed quote on the notional.",
    ),
    9527: FixFieldDefinition(
        9527, "CompetingQuoteMargin", "PRICEOFFSET", "Applied margin, if visible to the requester."
    ),
    9528: _price(9528, "CompetingQuoteAskSpotRate", "Ask spot rate (two-way competing quotes)."),
    9529: _price(9529, "CompetingQuoteBidSpotRate", "Bid spot rate (two-way competing quotes)."),
    9530: _price(9530, "CompetingQuoteAskForwardRate", "Ask forward rate (near leg for swaps)."),
    9531: _price(9531, "CompetingQuoteBidForwardRate", "Bid forward rate (near leg for swaps)."),
    9532: _price(
        9532, "CompetingQuoteAskFarLegForwardRate", "Ask forward rate for the far leg of a swap."
    ),
    9533: _price(
        9533, "CompetingQuoteBidFarLegForwardRate", "Bid forward rate for the far leg of a swap."
    ),
    9534: _price(9534, "CompetingQuoteAskForwardPoints", "Ask forward points."),
    9535: _price(9535, "CompetingQuoteBidForwardPoints", "Bid forward points."),
    9536: _price(9536, "CompetingQuoteAskSwapPoints", "Ask swap points."),
    9537: _price(9537, "CompetingQuoteBidSwapPoints", "Bid swap points."),
    9538: FixFieldDefinition(
        9538, "CompetingQuoteAskPremiumAmount", "QTY", "Ask premium amount (FX options)."
    ),
    9539: FixFieldDefinition(
        9539, "CompetingQuoteBidPremiumAmount", "QTY", "Bid premium amount (FX options)."
    ),
    9540: _price(9540, "CompetingQuoteAskQuoteValue", "Ask quote value (FX options)."),
    9541: _price(9541, "CompetingQuoteBidQuoteValue", "Bid quote value (FX options)."),
    9542: FixFieldDefinition(
        9542, "CompetingQuoteAskQuoteValueType", "STRING", "Ask quote value type (PERCENT/PIPS)."
    ),
    9543: FixFieldDefinition(
        9543, "CompetingQuoteBidQuoteValueType", "STRING", "Bid quote value type (PERCENT/PIPS)."
    ),
}

# Reference-price group (9780) members.
_REF_PRICE_TAGS: dict[int, FixFieldDefinition] = {
    9780: FixFieldDefinition(9780, "NoRefprices", "NUMINGROUP", "Number of reference prices."),
    9781: FixFieldDefinition(9781, "RefPriceSource", "STRING", "Source of the reference price."),
    9782: FixFieldDefinition(
        9782,
        "RefPriceSnapshotEvent",
        "STRING",
        "EMS event at which the reference price was captured.",
    ),
    9783: FixFieldDefinition(
        9783, "RefPriceSnapshotTime", "UTCTIMESTAMP", "Timestamp of the reference price."
    ),
    9784: _price(9784, "RefPriceAskSpotRate", "Ask spot rate of this reference price."),
    9785: _price(9785, "RefPriceMidSpotRate", "Mid spot rate of this reference price."),
    9786: _price(9786, "RefPriceBidSpotRate", "Bid spot rate of this reference price."),
    9787: _price(9787, "RefPriceAskForwardRate", "Ask forward rate of this reference price."),
    9788: _price(9788, "RefPriceMidForwardRate", "Mid forward rate of this reference price."),
    9789: _price(9789, "RefPriceBidForwardRate", "Bid forward rate of this reference price."),
    9790: _price(9790, "RefPriceAskSwapPoints", "Ask swap points of this reference price."),
    9791: _price(9791, "RefPriceMidSwapPoints", "Mid swap points of this reference price."),
    9792: _price(9792, "RefPriceBidSwapPoints", "Bid swap points of this reference price."),
}

# Venue custom / proprietary tags for the TI ExecutionReport. Standard FIX 4.4
# tags (6, 14, 17, 22, 29, 31, 32, 37, 38, 39, 48, 54, 55, 60, 64, 75, 150, 151,
# 159, 167, 192, 193, 194, 195, 201, 202, 230, 447/448/452/453, 454/455/456, 460,
# 461, 523/802/803, 526, 527, 541, 641, 687, 696, 697, 828, 916, 917, 947, 996,
# 2376, 2668/2669/2670, 1903/1906/1907) come from the default dict.
_360T_TI_CUSTOM_TAGS: dict[int, FixFieldDefinition] = {
    # Product family — TI enum values (differ from the RFS handler's FX-STD/FX-BT).
    7071: FixFieldDefinition(
        7071,
        "ProductType",
        "STRING",
        "360T product family (TradeImporter values).",
        {
            "FX-SPOT": "Spot",
            "FX-FWD": "Forward",
            "FX-NDF": "Non-Deliverable Forward",
            "FX-SWAP": "Swap",
            "FX-OPTION": "Option",
            "FX-TIME-OPTION": "FX Time Option",
            "MM": "Money Market (Loan / Deposit / Prolongation)",
            "MM Fund": "Money Market Fund",
            "Tri-Party Repo": "TriParty Repo",
            "FX-FUTURE": "FX Future",
            "EFP": "Exchange for Physical",
        },
    ),
    # Far-leg executed rate for swaps (also NotionalDeltaExchange for fx options).
    6160: _price(6160, "LastPx2", "FX Swap: far-leg executed rate (ExecutionReport)."),
    # Settlement / value-date variants.
    7657: FixFieldDefinition(
        7657,
        "SettlDateQuoteCur",
        "LOCALMKTDATE",
        "Quote-currency settle date for a split value date (near leg).",
    ),
    7658: FixFieldDefinition(
        7658,
        "SettlDate2QuoteCur",
        "LOCALMKTDATE",
        "Quote-currency settle date for a split value date (far leg).",
    ),
    # Identifiers.
    7653: FixFieldDefinition(7653, "UTIID", "STRING", "Unique Trade Identifier for the product."),
    7659: FixFieldDefinition(
        7659, "UTIIDNear", "STRING", "Unique Trade Identifier for the near leg (swaps/NDS)."
    ),
    7660: FixFieldDefinition(
        7660, "UTIIDFar", "STRING", "Unique Trade Identifier for the far leg (swaps/NDS)."
    ),
    2891: FixFieldDefinition(
        2891, "UPICode", "STRING", "Unique Product Identifier (near leg for swaps/NDS)."
    ),
    7891: FixFieldDefinition(
        7891, "UPICode2", "STRING", "Unique Product Identifier of the far leg (swaps/NDS)."
    ),
    # Fixing (NDF / NDS / fixing orders).
    7075: FixFieldDefinition(
        7075, "FixingReference", "STRING", "Fixing reference for fixing orders, NDF and NDS."
    ),
    7543: FixFieldDefinition(
        7543, "FixingDate", "LOCALMKTDATE", "Fixing date for fixing orders, NDF and NDS (near leg)."
    ),
    7544: FixFieldDefinition(7544, "FixingTime", "UTCTIMESTAMP", "Fixing time for fixing orders."),
    7545: FixFieldDefinition(
        7545, "FixingDate2", "LOCALMKTDATE", "Fixing date for the far leg of an NDS."
    ),
    # Money market.
    7072: FixFieldDefinition(7072, "DayCount", "STRING", "Day-count convention for MM requests."),
    7600: FixFieldDefinition(
        7600,
        "InterestSettlType",
        "STRING",
        "Accrued-interest handling for MM prolongations (SETTLE/COMPOUND/NON-COMPOUND).",
    ),
    7601: FixFieldDefinition(
        7601,
        "ProlongationCounter",
        "INT",
        "How many times the original contract has been prolonged, incl. this time.",
    ),
    7602: FixFieldDefinition(
        7602, "OrigNotionalAmt", "QTY", "Notional of the contract being prolonged (MM)."
    ),
    7603: FixFieldDefinition(
        7603, "OrigExecID", "STRING", "Reference ID of the contract being prolonged (MM/FX)."
    ),
    7604: FixFieldDefinition(
        7604, "LastExec", "STRING", "Reference ID of the last prolongation (MM/FX)."
    ),
    9603: FixFieldDefinition(
        9603, "BusinessAdjustment", "STRING", "Business-day convention for loans/deposits."
    ),
    # Options.
    9601: FixFieldDefinition(9601, "Cutoff", "STRING", "Cutoff / expiry time for options."),
    # FX Time Option.
    9514: FixFieldDefinition(9514, "OptionPeriod", "STRING", "FX Time Option period."),
    9515: FixFieldDefinition(9515, "OptionDate", "LOCALMKTDATE", "FX Time Option end date."),
    # Execution-venue / SEF / regulatory.
    7611: FixFieldDefinition(
        7611,
        "ExecutionVenueType",
        "STRING",
        "Type of execution venue.",
        {"1": "SEF", "2": "OFF-FACILITY", "3": "MTF"},
    ),
    7612: FixFieldDefinition(
        7612, "ExecutionVenue", "STRING", "Execution venue (360T for SEF; MIC for MTF)."
    ),
    7613: FixFieldDefinition(7613, "IsLargeTrade", "BOOLEAN", "SEF field isLargeTrade."),
    7614: FixFieldDefinition(
        7614, "RequiredTransaction", "BOOLEAN", "SEF field requiredTransaction."
    ),
    7615: FixFieldDefinition(
        7615, "ReportingParty", "STRING", "Reporting party LEI/name (deprecated; see NoPartyIDs)."
    ),
    7616: FixFieldDefinition(7616, "SwapDataRepository", "STRING", "SEF field SDR (name or LEI)."),
    7617: FixFieldDefinition(7617, "ClearingExempted", "BOOLEAN", "SEF field clearingExempted."),
    7618: FixFieldDefinition(
        7618, "Clearer", "STRING", "Name of the clearing institution / SEF clearer."
    ),
    7619: FixFieldDefinition(
        7619,
        "RequesterPersonStatus",
        "STRING",
        "SEF status of the requester individual (1=US, 2=NON-US).",
    ),
    7620: FixFieldDefinition(7620, "OriginatingLEI", "STRING", "SEF field originating LEI."),
    7621: FixFieldDefinition(7621, "ProviderLEI", "STRING", "SEF field provider LEI."),
    7626: FixFieldDefinition(
        7626,
        "ClearingStatus",
        "STRING",
        "Clearing status of the trade.",
        {"PENDING": "Pending", "CLEARED": "Cleared", "REJECTED": "Rejected", "FAILED": "Failed"},
    ),
    7627: FixFieldDefinition(
        7627,
        "ProviderPersonStatus",
        "STRING",
        "SEF status of the provider individual (1=US, 2=NON-US).",
    ),
    # Misc trade attributes.
    7074: FixFieldDefinition(
        7074, "IsItex", "BOOLEAN", "Set if this trade is an internal ITEX trade."
    ),
    7706: FixFieldDefinition(
        7706, "FXSecurityConversion", "BOOLEAN", "Marks the trade as an FX security conversion."
    ),
    7708: FixFieldDefinition(
        7708, "NegotiationType", "STRING", "Negotiation strategy used on the 360T platform."
    ),
    7670: FixFieldDefinition(7670, "MMCHedgeTrigger", "STRING", "Trigger for the hedge from MMC."),
    7671: FixFieldDefinition(
        7671, "MMCHedgeTriggerBy", "STRING", "Trader who closed the position in MMC."
    ),
    7672: FixFieldDefinition(
        7672,
        "IsAutoPriceManualIntervention",
        "BOOLEAN",
        "Auto pricing was intervened by a manual trader.",
    ),
    # Margins / spreads.
    9550: FixFieldDefinition(
        9550, "SpotMargin", "PRICEOFFSET", "Spot margin (near leg for swaps/NDS)."
    ),
    9551: FixFieldDefinition(
        9551, "ForwardPointMargin", "PRICEOFFSET", "Forward-point margin (near leg)."
    ),
    9552: FixFieldDefinition(
        9552, "TotalMargin", "PRICEOFFSET", "Sum of spot and forward margin (near leg)."
    ),
    9553: FixFieldDefinition(
        9553, "SpotTraderSpread", "PRICEOFFSET", "Spot trader spread (near leg)."
    ),
    9554: FixFieldDefinition(
        9554, "ForwardTraderSpread", "PRICEOFFSET", "Forward trader spread (near leg)."
    ),
    9555: FixFieldDefinition(9555, "SpotMargin2", "PRICEOFFSET", "Spot margin for the far leg."),
    9556: FixFieldDefinition(
        9556, "ForwardPointMargin2", "PRICEOFFSET", "Forward-point margin for the far leg."
    ),
    9557: FixFieldDefinition(
        9557, "TotalMargin2", "PRICEOFFSET", "Total margin (spot+forward) for the far leg."
    ),
    9558: FixFieldDefinition(
        9558, "SpotTraderSpread2", "PRICEOFFSET", "Spot trader spread for the far leg."
    ),
    9559: FixFieldDefinition(
        9559, "ForwardTraderSpread2", "PRICEOFFSET", "Forward trader spread for the far leg."
    ),
    # Ex-ante cost.
    9754: _price(9754, "ExAnteCost", "Ex-ante costs in EUR."),
    9755: _price(9755, "ExAnteCostPercentage", "Ex-ante costs in percentage."),
    9756: _price(
        9756, "ExAnteCostExchangeRate", "Exchange rate used to express the ex-ante cost in EUR."
    ),
    # Commodity (decode only).
    7538: FixFieldDefinition(
        7538, "TenorValue", "STRING", "Prompt date of a metals product (front leg for spreads)."
    ),
    7539: FixFieldDefinition(
        7539, "TenorValue2", "STRING", "Prompt date of the back leg of a metals spread."
    ),
    7540: FixFieldDefinition(
        7540, "CommodityPeriod", "STRING", "Period definition for commodity trading."
    ),
    7565: FixFieldDefinition(
        7565, "CommoditySwapAverage", "STRING", "Averaging frequency (DAILY/MONTHLY/QUARTERLY)."
    ),
    7566: FixFieldDefinition(
        7566, "CommoditySwapCashSettlementType", "STRING", "Single or multiple payment."
    ),
    7567: FixFieldDefinition(
        7567,
        "CommoditySwapCashSettlementDate",
        "LOCALMKTDATE",
        "Payment date for a single-payment commodity swap.",
    ),
    7568: FixFieldDefinition(
        7568, "CommoditySwapFixingSource", "STRING", "Benchmark/contract that determines the price."
    ),
    # Custom-fields group (shared count tag 7546 with RFS).
    7546: FixFieldDefinition(
        7546, "NoCustomFields", "NUMINGROUP", "Number of 360T custom field entries."
    ),
    7547: FixFieldDefinition(7547, "CustomFieldsName", "STRING", "Name of a 360T custom field."),
    7548: FixFieldDefinition(7548, "CustomFieldsValue", "STRING", "Value of a 360T custom field."),
    # Payment-schedule group.
    7560: FixFieldDefinition(
        7560, "NoPaymentSchedule", "NUMINGROUP", "Number of payment-schedule entries."
    ),
    7561: FixFieldDefinition(
        7561, "PaymentScheduleYearMonth", "MONTHYEAR", "Payment month (yyyyMM)."
    ),
    7562: FixFieldDefinition(
        7562, "PaymentScheduleAmount", "QTY", "Paid amount for the schedule entry."
    ),
    # Negotiation-id group.
    9580: FixFieldDefinition(
        9580, "NoNegotiationExternalIds", "NUMINGROUP", "Number of negotiation ids."
    ),
    9581: FixFieldDefinition(9581, "NegotiationExternalId", "STRING", "A negotiation id."),
    # TI product-id mapping group.
    9590: FixFieldDefinition(
        9590, "NoTIProductIds", "NUMINGROUP", "Number of product-id mappings."
    ),
    9591: FixFieldDefinition(9591, "TIProductId", "STRING", "A trade-intention product id."),
    9592: FixFieldDefinition(9592, "TIExternalId", "STRING", "The trade-intention's external id."),
    # Reference-id group.
    9800: FixFieldDefinition(9800, "NoReferenceIDs", "NUMINGROUP", "Number of reference ids."),
    9801: FixFieldDefinition(9801, "ReferenceIDType", "STRING", "Type of the reference id."),
    9802: FixFieldDefinition(9802, "ReferenceIDValue", "STRING", "Reference id value."),
    **_COMPETING_QUOTE_TAGS,
    **_REF_PRICE_TAGS,
}

# Standard tags 360T TI assigns venue-specific or extended enum values to.
_360T_TI_ENUM_EXTENSIONS: dict[int, dict[str, str]] = {
    54: {
        "1": "Buy",
        "2": "Sell",
        "G": "Borrow (MM financing — collateral direction)",
        "F": "Lend / Deposit (MM financing)",
    },
    22: {"4": "ISIN", "101": "MM Fund Provider Identifier"},
    201: {"0": "Put", "1": "Call"},
    29: {
        "1": "AOTC (any other capacity)",
        "3": "MTCH (matched principal)",
        "4": "DEAL (dealing on own account)",
    },
    447: {
        "D": "Proprietary custom code",
        "G": "MIC",
        "N": "Legal Entity Identifier",
        "P": "Short code identifier",
    },
    452: {
        "1": "Executing Firm (requester)",
        "4": "Clearing Firm",
        "12": "Executing Trader",
        "14": "Clearing Broker",
        "33": "Interested Party (export target)",
        "35": "Liquidity Provider",
        "63": "Systematic Internaliser (SI)",
        "64": "Multilateral Trading Facility (MTF)",
        "73": "Execution Venue (360T SEF)",
        "78": "Allocation Entity",
        "116": "Reporting Party",
        "122": "Investment Decision Maker",
    },
    456: {
        "4": "ISIN",
        "001": "Contract code (FX Future / EFP)",
        "002": "Product ID (FX Future / EFP)",
        "003": "Instrument ID (FX Future / EFP)",
    },
    828: {"65": "TPAC (Package Trade)"},
    1906: {
        "2": "Block",
        "5": "Trading venue transaction identifier (TVTIC)",
        "6": "Reporting tracking number (RTN)",
    },
    2376: {"22": "Algorithm", "24": "Natural person"},
}


class ThreeSixtyTTIHandler(VenueHandler):
    """Handler for 360T TradeImporter (post-trade STP) FIX messages."""

    # Product family values that uniquely mark a TI ExecutionReport.
    _TI_PRODUCT_TYPES = frozenset(
        {
            "FX-SPOT",
            "FX-FWD",
            "FX-NDF",
            "FX-SWAP",
            "FX-OPTION",
            "FX-TIME-OPTION",
            "MM",
            "MM Fund",
            "Tri-Party Repo",
            "FX-FUTURE",
            "EFP",
            "Commodity Asian-Swap",
            "Commodity Bullet-Swap",
            "Energy Asian-Option",
            "Metals Outright",
            "Metals Spread",
            "Metals Quarterly Strip",
        }
    )
    _TI_COMPIDS = frozenset({"360T_TI"})

    # Display names for the products that get full Trade-Summary extraction;
    # other products fall through to the raw 7071 value.
    _PRODUCT_LABELS = {
        "FX-SPOT": "Spot",
        "FX-FWD": "Forward",
        "FX-NDF": "NDF",
        "FX-SWAP": "Swap",
        "FX-OPTION": "FX Option",
        "FX-TIME-OPTION": "FX Time Option",
        "MM": "Money Market",
        "MM Fund": "MM Fund",
        "Tri-Party Repo": "TriParty Repo",
        "FX-FUTURE": "FX Future",
        "EFP": "EFP",
    }

    @property
    def name(self) -> str:
        return "360T TI"

    @property
    def sender_comp_ids(self) -> list[str]:
        # The _TI suffix is matched on whichever of tags 49/56 carries it, so a
        # single alias covers both directions (360T_TI ↔ client *_TI).
        return ["360T_TI"]

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        return list(_360T_TI_CUSTOM_TAGS.values())

    @property
    def enum_extensions(self) -> dict[int, dict[str, str]]:
        return _360T_TI_ENUM_EXTENSIONS

    # -- Detection --------------------------------------------------------

    def claims_message(self, message: FixMessage) -> bool:
        """Claim a message as 360T TI by protocol/content.

        Requires an ExecutionReport plus a 360T-TI-specific marker, so it can
        never steal RFS traffic (which uses FX-STD/FX-BT and the 360T CompID) or
        any other venue's messages.
        """
        if message.msg_type != "8":
            return False
        if message.get_value(7071) in self._TI_PRODUCT_TYPES:
            return True
        if message.get_value(9516):
            return True
        for tag in (49, 56):
            value = message.get_value(tag)
            if value and value.upper() in self._TI_COMPIDS:
                return True
        return False

    # -- Product ----------------------------------------------------------

    def _derive_product(self, message: FixMessage) -> str | None:
        """Derive the product from ProductType(7071).

        NDS is a swap-shaped trade distinguished by a far-leg fixing date (7545).
        """
        product_type = message.get_value(7071)
        if product_type == "FX-SWAP" and message.get_value(7545):
            return "NDS"
        if product_type is None:
            return None
        return self._PRODUCT_LABELS.get(product_type, product_type)

    # -- Enrichment -------------------------------------------------------

    def enhance_message(self, message: FixMessage) -> FixMessage:
        message = super().enhance_message(message)
        product = self._derive_product(message)
        if product:
            message.product_type = product
        for tag, key in (
            (7611, "execution_venue_type"),
            (7612, "execution_venue"),
            (7653, "uti"),
            (7659, "uti_near"),
            (7660, "uti_far"),
            (7626, "clearing_status"),
        ):
            value = message.get_value(tag)
            if value:
                message.venue_extras[key] = value
        return message

    # -- Trade extraction -------------------------------------------------

    def extract_trade(self, message: FixMessage) -> ParsedTrade:
        trade = super().extract_trade(message)
        # TI always sends LastShares(32)=0; the traded notional is in OrderQty(38).
        trade.quantity = _to_float(message.get_value(38))

        product = self._derive_product(message)
        if product not in ("Swap", "NDS"):
            # Options carry a premium in OrderQty2(192) and MM carries an end
            # date in SettlDate2(193); the base handler would mistake either for
            # a swap. Clear any swap economics it set.
            self._clear_swap_fields(trade)
            return trade

        self._refine_swap(message, trade)
        return trade

    def _refine_swap(self, message: FixMessage, trade: ParsedTrade) -> None:
        """Apply 360T TI swap economics on top of the base extraction."""
        trade.is_swap = True

        if trade.near_leg_price is None:
            trade.near_leg_price = _to_float(message.get_value(31) or message.get_value(44))
        trade.near_quantity = _to_float(message.get_value(38))
        trade.far_quantity = _to_float(message.get_value(192))
        trade.far_settlement_date = trade.far_settlement_date or message.get_value(193)

        base, term = parse_symbol(trade.symbol)
        side_code = message.get_value(54)
        # 360T Side(54) is relative to the base currency (ccy1) and, for swaps,
        # to the far leg. Reuse swap_side_actions with the base currency as the
        # "trade currency" so actions read e.g. "Buy GBP" / "Sell GBP".
        if base and side_code in ("1", "2"):
            near_action, far_action = swap_side_actions(side_code, base, base, term)
            trade.near_leg_action = near_action
            trade.far_leg_action = far_action
            trade.swap_side_source = "360t"

        # TI carries the far-leg executed rate in LastPx2(6160).
        far_exec = _to_float(message.get_value(6160))
        if far_exec is not None:
            trade.far_leg_price = far_exec
            if trade.near_leg_price is not None:
                trade.swap_points = far_exec - trade.near_leg_price
                ps = trade.pip_size or pip_size(trade.symbol)
                if ps:
                    trade.swap_points_pips = trade.swap_points / ps

    @staticmethod
    def _clear_swap_fields(trade: ParsedTrade) -> None:
        """Reset any swap economics the base handler may have set."""
        trade.is_swap = False
        trade.near_leg_price = None
        trade.far_leg_price = None
        trade.near_quantity = None
        trade.far_quantity = None
        trade.swap_points = None
        trade.swap_points_pips = None
        trade.near_leg_action = None
        trade.far_leg_action = None
        trade.swap_side_source = None
        trade.spot_rate = None
        trade.far_settlement_date = None
