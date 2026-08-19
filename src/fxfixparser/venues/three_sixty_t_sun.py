"""360T SUN (Swap User Network) venue handler.

Supports the 360 Treasury Systems (Deutsche Boerse) **SUN** FIX API — the
anonymous, fully automated FX Swap limit order book run as a 360T MTF. It is
the third 360T FIX interface modelled here, alongside the RFS Market Taker
(``three_sixty_t.py``) and the TradeImporter post-trade feed
(``three_sixty_t_ti.py``).

Written against the *Swap User Network (SUN) API — FIX Rules of Engagement*
v2.16 (platform release 4.27).

Characteristics of the SUN API:

* FIX 5.0 SP2 over a FIXT 1.1 session layer (``1128=9``), so the bundled
  ``spec/FIX50SP2.xml`` is auto-loaded by the parser and the standard tag space
  decodes on its own. The FIX 5.0 tags SUN relies on are *also* defined here so
  a message that omits ApplVerID still decodes;
* every SUN instrument is two-legged — **FX Swap** (default), **NDS**
  (``ProductType(7071)=FX-NDS``) and **EFP** (``EFP``). There is no spot or
  outright product, so an economic SUN message is always a swap;
* orders are priced in **swap points**, not an all-in rate: ``Price(44)`` and
  ``LastPx(31)`` carry the points (the ROE calls them "swap pips"). The executed
  all-in rates ride in ``LastNearLegPx(9630)`` / ``LastFarLegPx(9631)`` on the
  standard ExecutionReport, and in ``LastPx(31)`` / ``LastPx2(6160)`` on the
  'Trade Export' ExecutionReport. See :meth:`ThreeSixtyTSUNHandler.extract_trade`;
* ``Side(54)`` is relative to the base currency of the **far** leg — the same
  360T convention the RFS and TI interfaces use;
* the SUN fill identifier is a numeric id prefixed ``EMSO-`` and travels in
  ``SecondaryExecID(527)`` (executions) and ``RefOrderID(1080)`` (credit check);
* matched orders trigger a bilateral credit check carried by
  PartyRiskLimitCheckRequest(DF) / …Ack(DG), which quote the matched notional
  per leg in a NoLegs(555) group.

Venue custom tags are defined in Python (no runtime XML), per the project's
proprietary-data policy.
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


def _qty(tag: int, name: str, desc: str) -> FixFieldDefinition:
    return FixFieldDefinition(tag, name, "QTY", desc)


def _date(tag: int, name: str, desc: str) -> FixFieldDefinition:
    return FixFieldDefinition(tag, name, "LOCALMKTDATE", desc)


# 360T's proprietary SUN tags (5xxx/6xxx/7xxx/9xxx). None of these exist in
# either bundled spec, so they would otherwise stay Unknown.
_SUN_PROPRIETARY_TAGS: dict[int, FixFieldDefinition] = {
    5241: _date(
        5241,
        "LastTradingDate",
        "EFP: last calendar date the futures contract can be traded before expiry.",
    ),
    5242: _date(
        5242,
        "UnderlyingLastTradingDate",
        "EFP (SecurityDefinition): last trading date of the futures contract.",
    ),
    6160: _price(
        6160,
        "LastPx2",
        "'Trade Export' ExecutionReport: executed all-in rate of the far leg.",
    ),
    6164: _qty(
        6164,
        "LeavesQty2",
        "Quantity of the far leg still open for execution (0 once the order is "
        "Filled, Cancelled or Rejected).",
    ),
    6165: _qty(6165, "CumQty2", "Cumulative executed quantity of the far leg."),
    7071: FixFieldDefinition(
        7071,
        "ProductType",
        "STRING",
        "SUN product family. Absence of the field denotes an FX Swap.",
        {
            "FX-SWAP": "FX Swap (default)",
            "FX-NDS": "Non-Deliverable Swap",
            "EFP": "Exchange for Physical",
        },
    ),
    7075: FixFieldDefinition(7075, "FixingReference", "STRING", "NDS: the fixing reference."),
    7543: _date(7543, "FixingDate", "NDS: fixing date of the near leg."),
    7545: _date(7545, "FixingDate2", "NDS: fixing date of the far leg."),
    7626: FixFieldDefinition(
        7626,
        "ClearingState",
        "STRING",
        "'Trade Export' ExecutionReport: clearing state at the clearing house.",
        {"1": "Novated", "2": "Failed", "4": "Sent", "5": "Rejected"},
    ),
    7629: FixFieldDefinition(7629, "ClearingTransactionId", "STRING", "Clearing transaction ID."),
    7630: FixFieldDefinition(
        7630, "ClearingTransactionTime", "STRING", "Clearing transaction time."
    ),
    7631: FixFieldDefinition(
        7631,
        "ClearingRejectionReason",
        "STRING",
        "Clearing rejection reason (sent when ClearingState is Rejected).",
    ),
    7891: FixFieldDefinition(
        7891, "UPICode2", "STRING", "Unique Product Identifier of the far leg."
    ),
    9611: _qty(9611, "LastOppositeQty", "Near-leg opposite amount executed for this order."),
    9612: _date(
        9612,
        "UnderlyingMaturityDate2",
        "SecurityDefinition: value date of the far leg in the 360T financial calendar.",
    ),
    9615: _qty(
        9615,
        "OrigCumQty",
        "Final filled quantity of the order that a successful "
        "OrderCancelReplaceRequest cancelled (ExecType=Replace).",
    ),
    9617: _qty(9617, "LastQty2", "Far-leg notional amount executed for this order."),
    9618: _qty(9618, "LastOppositeQty2", "Far-leg opposite amount executed for this order."),
    9622: _qty(
        9622, "LegOppositeOrderQty", "Opposite amount of this leg (credit-check NoLegs entry)."
    ),
    9630: _price(9630, "LastNearLegPx", "Executed all-in rate of the near leg."),
    9631: _price(9631, "LastFarLegPx", "Executed all-in rate of the far leg."),
    9752: FixFieldDefinition(
        9752,
        "StreamID",
        "INT",
        "Numerical identifier (1-127) of the client pricing segment the order "
        "belongs to. Not carried forward to a spot-sensitivity follow-up order.",
    ),
    9820: FixFieldDefinition(
        9820,
        "PipsAdjustment",
        "INT",
        "Spot sensitivity value (10-999) controlling when the order's swap pips "
        "are automatically adjusted with spot movement. 0 disables the feature.",
    ),
    9821: FixFieldDefinition(
        9821,
        "OppositeMatchingAllowed",
        "BOOLEAN",
        "Whether the order may match FX Swaps whose notional is specified in the "
        "other currency of the same pair. Defaults to false.",
    ),
    9822: FixFieldDefinition(
        9822,
        "UnevenSwapAllowed",
        "BOOLEAN",
        "Whether resulting trades may have unequal near-leg and far-leg "
        "notionals (the interest-rate component of the swap). Defaults to false.",
    ),
    9823: _date(9823, "UnderlyingFixingDate", "SecurityDefinition: fixing date of the near leg."),
    9824: _date(9824, "UnderlyingFixingDate2", "SecurityDefinition: fixing date of the far leg."),
    9825: FixFieldDefinition(
        9825, "UnderlyingFixingReference", "STRING", "SecurityDefinition (NDS): fixing reference."
    ),
}

# Standard FIX 5.0 SP2 tags SUN uses that the FIX 4.4 base dictionary does not
# define. The parser layers spec/FIX50SP2.xml automatically when a message
# carries ApplVerID(1128)=9, but SUN marks that header field optional — these
# keep the message legible when it is omitted, with SUN's own wording.
_SUN_FIX50_TAGS: dict[int, FixFieldDefinition] = {
    1070: FixFieldDefinition(
        1070,
        "MDQuoteType",
        "INT",
        "Quote type of a market-data entry.",
        {
            "0": "Indicative",
            "1": "Tradable (mid entries: active interest with a credit relationship)",
            "2": "Knocked-out interest at Mid where there is a credit relationship",
        },
    ),
    1080: FixFieldDefinition(
        1080,
        "RefOrderID",
        "STRING",
        "SUN fill identifier the credit check refers to — the same value as "
        "SecondaryExecID(527) on the ExecutionReport (numeric, 'EMSO-' prefixed).",
    ),
    1102: _price(
        1102,
        "TriggerPrice",
        "'Spot Sensitivity' spot rate: the order is cancelled if this spot level "
        "is touched while it is active.",
    ),
    1110: _price(
        1110,
        "TriggerNewPrice",
        "'Follow-up Price': limit price of the replacement order created when the "
        "spot-sensitivity level (TriggerPrice 1102) is touched.",
    ),
    1328: FixFieldDefinition(
        1328,
        "RejectText",
        "STRING",
        "Reason text; required when RiskLimitCheckRequestStatus(2325) is Rejected.",
    ),
    1822: FixFieldDefinition(
        1822,
        "MinQtyMethod",
        "INT",
        "How MinQty(110) applies. Required whenever MinQty is set.",
        {"2": "Multiple (applies to every execution)"},
    ),
    1903: FixFieldDefinition(
        1903,
        "RegulatoryTradeID",
        "STRING",
        "TVTIC or Report Tracking Number. A swap/NDS carries two or three "
        "entries: product level (where available), near leg and far leg.",
    ),
    1906: FixFieldDefinition(
        1906,
        "RegulatoryTradeIDType",
        "INT",
        "Type of regulatory trade ID.",
        {
            "5": "Trading venue transaction identifier (TVTIC)",
            "6": "Report Tracking Number (RTN)",
        },
    ),
    1907: FixFieldDefinition(
        1907, "NoRegulatoryTradeIDs", "NUMINGROUP", "Number of regulatory trade ID entries."
    ),
    2318: FixFieldDefinition(
        2318, "RiskLimitCheckRequestID", "STRING", "Unique ID of this credit-check request."
    ),
    2320: FixFieldDefinition(
        2320,
        "RiskLimitCheckTransType",
        "INT",
        "Transaction type of the credit check.",
        {"0": "New", "1": "Cancel (limit released / consumed notification)"},
    ),
    2321: FixFieldDefinition(
        2321,
        "RiskLimitCheckType",
        "CHAR",
        "Credit-check type. On the outgoing (360T -> customer) Ack this reports "
        "what happened to the reserved credit.",
        {"0": "Submit / Limit released (no trade)", "1": "Limit consumed (trade done)"},
    ),
    2323: FixFieldDefinition(
        2323,
        "RiskLimitCheckRequestType",
        "INT",
        "Fill treatment of the credit check.",
        {"0": "All or none"},
    ),
    2324: FixFieldDefinition(
        2324, "RiskLimitCheckAmount", "AMT", "Amount requested for credit approval."
    ),
    2325: FixFieldDefinition(
        2325,
        "RiskLimitCheckRequestStatus",
        "INT",
        "Outcome reported by the credit check.",
        {"0": "Approved", "2": "Rejected", "4": "Cancelled"},
    ),
    2326: FixFieldDefinition(
        2326,
        "RiskLimitCheckRequestResult",
        "INT",
        "Detailed result of the credit check.",
        {
            "0": "Successful",
            "1": "Invalid party",
            "2": "Requested amount exceeds credit limit",
            "3": "Requested amount exceeds clip size limit",
            "99": "Other",
        },
    ),
    2620: FixFieldDefinition(
        2620, "UnderlyingFutureID", "STRING", "EFP: futures contract code of the underlying."
    ),
    2621: FixFieldDefinition(
        2621,
        "UnderlyingFutureIDSource",
        "STRING",
        "Source of UnderlyingFutureID(2620).",
        {"8": "Exchange symbol"},
    ),
    2891: FixFieldDefinition(
        2891,
        "UPICode",
        "STRING",
        "Unique Product Identifier of the traded instrument (near leg for swaps).",
    ),
}

_SUN_CUSTOM_TAGS: dict[int, FixFieldDefinition] = {
    **_SUN_PROPRIETARY_TAGS,
    **_SUN_FIX50_TAGS,
}

# Standard tags SUN restricts or reinterprets. Merged over the default dict, so
# standard values survive and SUN's wording wins where they overlap.
_SUN_ENUM_EXTENSIONS: dict[int, dict[str, str]] = {
    # Side is the action on the base currency of the FAR leg, from the
    # participant's perspective — the 360T convention across all its APIs.
    54: {
        "1": "Buy (base currency of the far leg)",
        "2": "Sell (base currency of the far leg)",
    },
    40: {"2": "Limit", "P": "Pegged (mid-price peg; requires ExecInst M)"},
    18: {"M": "Mid-price peg (required when OrdType=P)"},
    59: {"0": "Day (or session)", "3": "Immediate or Cancel (IOC)", "6": "Good Till Date (GTD)"},
    150: {
        "0": "New",
        "4": "Cancelled",
        "5": "Replace",
        "8": "Rejected",
        "D": "Restated (swap pips repriced — see ExecRestatementReason 378)",
        "F": "Trade",
        "I": "Order Status",
        "K": "Clearing House report (state in ClearingState 7626)",
    },
    378: {"3": "Repricing of order"},
    103: {
        "6": "Duplicate order",
        "15": "Unknown account",
        "99": "Other",
        "100": "Credit check failed",
    },
    102: {"0": "Too late to cancel", "1": "Unknown order", "99": "Other (detail in Text 58)"},
    380: {
        "0": "Other",
        "3": "Unsupported message type",
        "5": "Conditionally required field missing",
    },
    321: {"3": "Request list securities"},
    323: {"4": "List of securities returned per request"},
    394: {"3": "No bidding process"},
    388: {"2": "Related to primary price"},
    842: {"1": "Basis points (pips)"},
    263: {"1": "Snapshot + Updates (subscribe)", "2": "Unsubscribe"},
    264: {"0": "Full book"},
    265: {"0": "Full refresh"},
    266: {"N": "All price entries are shown", "Y": "Entries at the same price are aggregated"},
    269: {"0": "Bid", "1": "Offer", "H": "Mid-price"},
    22: {"8": "Exchange symbol"},
    167: {"FUT": "Future (EFP)"},
    456: {"4": "ISIN"},
    447: {
        "D": "Proprietary custom code",
        "G": "MIC",
        "N": "Legal Entity Identifier",
        "P": "Short code identifier",
    },
    452: {
        "1": "Executing Firm",
        "4": "Clearing Firm",
        "11": "Order Origination Trader",
        "12": "Executing Trader",
        "17": "Contra Firm",
        "37": "Contra Trader",
        "64": "Multilateral Trading Facility (MTF)",
        "122": "Investment decision maker",
    },
    2376: {"22": "Algorithm", "24": "Natural person"},
    828: {"65": "TPAC (Package Trade)"},
    2669: {"0": "Pre-trade transparency waiver", "1": "Post-trade deferral"},
    2670: {
        "4": "No public price quoted as instrument is illiquid",
        "7": "Deferral due to illiquid instrument",
    },
    2594: {"2": "Liquidity provision activity order"},
}


class ThreeSixtyTSUNHandler(VenueHandler):
    """Handler for 360T SUN (Swap User Network) FIX messages."""

    # SUN product families. Absence of ProductType(7071) means FX Swap.
    _PRODUCT_LABELS = {"FX-SWAP": "Swap", "FX-NDS": "NDS", "EFP": "EFP"}

    # Message types that name a tradeable instrument. Session and
    # order-management messages (Logon, OrderCancelRequest, OrderStatusRequest,
    # OrderCancelReject, SecurityDefinition(Request), MarketDataRequestReject,
    # BusinessMessageReject) have no product. MarketDataSnapshotFullRefresh(W)
    # is included so a SUN swap-points book is labelled with its real product
    # rather than the generic product registry's Spot fallback.
    _PRODUCT_MSG_TYPES = frozenset({"D", "E", "G", "8", "DF", "DG", "W"})

    # Of those, the ones that describe a single trade and so carry economics to
    # extract. A book snapshot names an instrument but has no trade.
    _TRADE_MSG_TYPES = frozenset({"D", "E", "G", "8", "DF", "DG"})

    # The credit-check pair exists in both directions; only the leg-bearing
    # (360T -> customer) form describes an instrument, so those two types also
    # require a Symbol before a product is named.
    _CREDIT_CHECK_MSG_TYPES = frozenset({"DF", "DG"})

    # SUN fill identifiers are numeric with this prefix (SecondaryExecID 527 /
    # RefOrderID 1080) — a reliable SUN marker on the wire.
    _FILL_ID_PREFIX = "EMSO-"

    # Tags no other supported venue sends. Any one of them identifies SUN even
    # when the session CompIDs are client-specific.
    _SUN_ONLY_TAGS = (
        2318,  # RiskLimitCheckRequestID
        6164,  # LeavesQty2
        6165,  # CumQty2
        9611,  # LastOppositeQty
        9612,  # UnderlyingMaturityDate2
        9615,  # OrigCumQty
        9617,  # LastQty2
        9618,  # LastOppositeQty2
        9622,  # LegOppositeOrderQty
        9630,  # LastNearLegPx
        9631,  # LastFarLegPx
        9752,  # StreamID
        9820,  # PipsAdjustment
        9821,  # OppositeMatchingAllowed
        9822,  # UnevenSwapAllowed
        9823,  # UnderlyingFixingDate
        9824,  # UnderlyingFixingDate2
        9825,  # UnderlyingFixingReference
    )

    # Credit-check messages exist only on SUN among the supported venues.
    _SUN_ONLY_MSG_TYPES = frozenset({"DF", "DG"})

    @property
    def name(self) -> str:
        return "360T SUN"

    @property
    def sender_comp_ids(self) -> list[str]:
        # 360T issues per-client CompIDs for SUN sessions ("360T will provide
        # the values for SenderCompID/TargetCompID"), so these are conventional
        # aliases; content-based detection in claims_message does the real work.
        return ["360T_SUN", "360TSUN", "SUN"]

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        return list(_SUN_CUSTOM_TAGS.values())

    @property
    def enum_extensions(self) -> dict[int, dict[str, str]]:
        return _SUN_ENUM_EXTENSIONS

    # -- Detection --------------------------------------------------------

    def claims_message(self, message: FixMessage) -> bool:
        """Claim SUN traffic by its own dialect markers.

        SUN sessions use client-specific CompIDs, so detection leans on content:
        a SUN-only tag, a credit-check message type, the ``EMSO-`` fill-id
        prefix, or the NDS product code. Every marker is absent from RFS and TI
        traffic, so this can never steal a sibling 360T interface's messages —
        which matters because SUN is consulted before TI (both use
        ``ProductType(7071)=FX-SWAP``).
        """
        for tag in (49, 56):
            value = (message.get_value(tag) or "").upper()
            if value in {cid.upper() for cid in self.sender_comp_ids} or value.endswith("_SUN"):
                return True
        if message.msg_type in self._SUN_ONLY_MSG_TYPES:
            return True
        for tag in self._SUN_ONLY_TAGS:
            if message.get_value(tag) is not None:
                return True
        for tag in (527, 1080):
            value = message.get_value(tag) or ""
            if value.startswith(self._FILL_ID_PREFIX):
                return True
        # FX-NDS is SUN's own product code (RFS uses FX-STD, TI uses FX-NDF).
        return message.get_value(7071) == "FX-NDS"

    # -- Product ----------------------------------------------------------

    def _derive_product(self, message: FixMessage) -> str | None:
        """Name the SUN product, or None for a non-economic message."""
        if message.msg_type not in self._PRODUCT_MSG_TYPES:
            return None
        if message.msg_type in self._CREDIT_CHECK_MSG_TYPES and not message.get_value(55):
            # Customer -> 360T credit-check Ack: an approval/rejection only, no
            # instrument.
            return None
        product_type = message.get_value(7071) or "FX-SWAP"
        return self._PRODUCT_LABELS.get(product_type, product_type)

    # -- Enrichment -------------------------------------------------------

    def enhance_message(self, message: FixMessage) -> FixMessage:
        message = super().enhance_message(message)
        product = self._derive_product(message)
        if product:
            message.product_type = product
        for tag, key in (
            (527, "fill_id"),
            (1080, "credit_check_fill_id"),
            (2318, "risk_limit_check_request_id"),
            (9752, "stream_id"),
            (7626, "clearing_state"),
            (2891, "upi"),
            (7891, "upi_far"),
            (66, "list_id"),
            (9611, "near_opposite_qty"),
            (9618, "far_opposite_qty"),
        ):
            value = message.get_value(tag)
            if not value:
                continue
            # An order acknowledgement carries the placeholder SecondaryExecID 0
            # — there is no fill yet, so that is not an identifier to surface.
            if tag == 527 and value == "0":
                continue
            message.venue_extras[key] = value
        return message

    # -- Trade extraction -------------------------------------------------

    def extract_trade(self, message: FixMessage) -> ParsedTrade:
        """Extract SUN trade economics.

        Beyond the shared extraction this applies three SUN conventions:

        1. **Every SUN instrument is a swap** (FX Swap / NDS / EFP), so the
           trade is flagged as one even on messages that carry no far-leg tags.
        2. **Prices are swap points, not rates.** ``Price(44)`` / ``LastPx(31)``
           quote the points; the all-in rates are ``LastNearLegPx(9630)`` /
           ``LastFarLegPx(9631)`` (standard ExecutionReport) or ``LastPx(31)`` /
           ``LastPx2(6160)`` ('Trade Export' ExecutionReport). Swap points are
           computed from the two all-in rates whenever both are known; failing
           that the quoted points are surfaced in pips (the unit the ROE calls
           "swap pips"). The raw points are never left in ``trade.price``.
        3. **Side(54) applies to the base currency of the far leg**, as on the
           other two 360T interfaces.
        """
        trade = super().extract_trade(message)
        if message.msg_type not in self._TRADE_MSG_TYPES:
            return trade  # session / market-data message — no trade to enrich
        if self._derive_product(message) is None:
            return trade  # credit-check acknowledgement without an instrument

        trade.is_swap = True
        base, term = parse_symbol(trade.symbol)
        trade.base_currency = trade.base_currency or base
        trade.term_currency = trade.term_currency or term
        trade.trade_currency = trade.trade_currency or message.get_value(15)
        trade.far_settlement_date = trade.far_settlement_date or message.get_value(193)

        self._apply_quantities(message, trade)
        self._apply_prices(message, trade)

        # Side semantics: 360T applies Side to the base currency on the far leg,
        # so pass the base currency as the "trade currency" and the near leg
        # reads as the opposite.
        side_code = message.get_value(54)
        if base and side_code in ("1", "2"):
            near_action, far_action = swap_side_actions(side_code, base, base, term)
            trade.near_leg_action = near_action
            trade.far_leg_action = far_action
            trade.swap_side_source = "360t"

        return trade

    @staticmethod
    def _apply_quantities(message: FixMessage, trade: ParsedTrade) -> None:
        """Resolve near/far notionals.

        ``LastQty(32)`` is the executed amount on a fill but is fixed at 0 on
        order acknowledgements and on every 'Trade Export' ExecutionReport, so
        it is only used when non-zero; ``OrderQty(38)`` is the fallback. The
        far leg mirrors that with ``LastQty2(9617)`` / ``OrderQty2(192)``.
        """
        last_qty = _to_float(message.get_value(32))
        order_qty = _to_float(message.get_value(38))
        near_qty = last_qty if last_qty else order_qty
        if near_qty is not None:
            trade.quantity = near_qty
            trade.near_quantity = near_qty
        elif trade.quantity is None:
            # Credit-check messages carry no order quantity; the notional under
            # check is RiskLimitCheckAmount(2324). The per-leg amounts stay as
            # the NoLegs group reported them — they differ on an uneven swap.
            trade.quantity = _to_float(message.get_value(2324))

        last_qty2 = _to_float(message.get_value(9617))
        order_qty2 = _to_float(message.get_value(192))
        far_qty = last_qty2 if last_qty2 else order_qty2
        if far_qty is not None:
            trade.far_quantity = far_qty
        elif trade.far_quantity is None:
            # An even swap (UnevenSwapAllowed=false, the default) settles the
            # same notional on both legs.
            trade.far_quantity = trade.near_quantity

    @staticmethod
    def _apply_prices(message: FixMessage, trade: ParsedTrade) -> None:
        """Resolve all-in leg rates, the spot reference and the swap points."""
        near_all_in = _to_float(message.get_value(9630))
        far_all_in = _to_float(message.get_value(9631))
        # 'Trade Export' ExecutionReport: near all-in in LastPx(31), far in
        # LastPx2(6160). LastPx2 is the discriminator — the standard report
        # never carries it.
        if message.get_value(6160) is not None:
            if near_all_in is None:
                near_all_in = _to_float(message.get_value(31))
            far_all_in = _to_float(message.get_value(6160))
        elif near_all_in is None and far_all_in is None and message.get_value(555):
            # Credit-check legs: the shared extraction already read the per-leg
            # all-in rates out of LegPrice(566).
            near_all_in, far_all_in = trade.near_leg_price, trade.far_leg_price

        # Assigned unconditionally: without an all-in rate there is no leg
        # price to show, and the shared extraction would otherwise leave the
        # swap points from LastPx(31) / Price(44) sitting in the near leg.
        trade.near_leg_price = near_all_in
        trade.far_leg_price = far_all_in

        # LastSpotRate(194) is the venue's spot reference. Without it there is
        # no spot to show: the near leg price is an all-in forward rate, and on
        # a points-only message it is not a rate at all.
        trade.spot_rate = _to_float(message.get_value(194))

        ps = pip_size(trade.symbol)
        trade.pip_size = ps
        if trade.near_leg_price is not None and trade.far_leg_price is not None:
            trade.swap_points = trade.far_leg_price - trade.near_leg_price
            if ps:
                trade.swap_points_pips = trade.swap_points / ps
        else:
            # Points-only message (order, acknowledgement, cancel/replace): the
            # venue quotes the swap points directly, in pips.
            points = _to_float(message.get_value(31))
            if not points:
                points = _to_float(message.get_value(44))
            if points is not None:
                trade.swap_points_pips = points
                trade.swap_points = points * ps if ps else None

        # Never let raw swap points masquerade as a rate (the shared extraction
        # fills trade.price from LastPx/Price).
        trade.price = trade.far_leg_price
