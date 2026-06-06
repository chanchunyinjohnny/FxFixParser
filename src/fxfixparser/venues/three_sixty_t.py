"""360T RFS Market Taker venue handler.

Supports the 360 Treasury Systems (Deutsche Boerse) RFS Market Taker FIX API
(v12.6) for FX Spot, Forward, Swap, NDF, NDS, FX Time Options and Block trades.
The venue is named "360T RFS"; its post-trade sibling is "360T TI"
(``three_sixty_t_ti.py``), mirroring the Bloomberg FXGO / DOR pair.

360T runs FIX 4.4 with no ApplVerID, so the FIX 5.0 spec is not auto-loaded;
every non-FIX44 tag 360T uses is defined here in ``custom_tags``. 360T also:

* sends no SecurityType(167) - product is derived from field combinations
  (see ``_derive_product_type``);
* treats Side(54) as relative to the base currency (ccy1), and for swaps to the
  far leg (see ``_refine_swap_execution``);
* carries swap far-leg prices in 6050/6051 (Quote) and 6160 (ExecutionReport),
  not the standard 640/9091 (see ``_refine_swap_quote`` / ``_refine_swap_execution``).

Venue custom tags are defined in Python (no runtime XML), per the project's
proprietary-data policy. See docs/plans/2026-06-04-360t-rfs-support-design.md.
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


# Venue-scoped tag definitions. FIX 4.4 standard tags are covered by FIX44.xml;
# these are 360T's proprietary 6000/7000/9000-range tags plus FIX 5.0 regulatory
# tags absent from FIX44.xml. Tags carrying a 360T-specific enum bake their
# valid_values in here (enum_extensions only augments existing definitions).
_360T_CUSTOM_TAGS: dict[int, FixFieldDefinition] = {
    7070: FixFieldDefinition(
        7070,
        "RefSpotDate",
        "LOCALMKTDATE",
        "Spot date in the 360T financial calendar; a Spot trade has " "SettlDate == RefSpotDate.",
    ),
    7071: FixFieldDefinition(
        7071,
        "ProductType",
        "STRING",
        "360T product family.",
        {"FX-STD": "Spot / Forward / Swap / NDF / NDS", "FX-BT": "Block trade"},
    ),
    7541: FixFieldDefinition(
        7541, "MaturityDate2", "LOCALMKTDATE", "Far-leg fixing date for an NDS."
    ),
    7546: FixFieldDefinition(
        7546, "NoCustomFields", "NUMINGROUP", "Number of 360T custom field entries."
    ),
    7547: FixFieldDefinition(7547, "CustomFieldName", "STRING", "Name of a 360T custom field."),
    7548: FixFieldDefinition(7548, "CustomFieldValue", "STRING", "Value of a 360T custom field."),
    7605: FixFieldDefinition(
        7605, "USIPrefix", "STRING", "Unique Swap Identifier prefix (near leg for swaps)."
    ),
    7606: FixFieldDefinition(
        7606, "USIID", "STRING", "Unique Swap Identifier (near leg for swaps)."
    ),
    7607: FixFieldDefinition(
        7607, "USIPrefix2", "STRING", "Unique Swap Identifier prefix (far leg)."
    ),
    7608: FixFieldDefinition(7608, "USIID2", "STRING", "Unique Swap Identifier (far leg)."),
    7611: FixFieldDefinition(
        7611,
        "ExecutionVenueType",
        "STRING",
        "Execution venue.",
        {"2": "OFF facility / OTC (default)", "3": "MTF"},
    ),
    7650: FixFieldDefinition(7650, "MidSpotRate", "PRICE", "Mid spot rate."),
    7651: FixFieldDefinition(7651, "MidPx2", "PRICE", "Mid price of the far leg (swaps)."),
    7652: FixFieldDefinition(
        7652,
        "LegMidPx",
        "PRICE",
        "Mid price for an individual leg (NoLegs member). Typed String in the "
        "360T spec; stored verbatim, surfaced as a price.",
    ),
    7653: FixFieldDefinition(
        7653, "UTI", "STRING", "Unique Trade Identifier (near leg for swaps)."
    ),
    7654: FixFieldDefinition(
        7654, "UTI2", "STRING", "Unique Trade Identifier (far leg for swaps)."
    ),
    6050: FixFieldDefinition(6050, "BidPx2", "PRICE", "FX Swap: far-leg bid forward rate (Quote)."),
    6051: FixFieldDefinition(
        6051, "OfferPx2", "PRICE", "FX Swap: far-leg offer forward rate (Quote)."
    ),
    6160: FixFieldDefinition(
        6160, "LastPx2", "PRICE", "FX Swap: far-leg executed rate (ExecutionReport)."
    ),
    9514: FixFieldDefinition(9514, "OptionPeriod", "STRING", "FX Time Option period."),
    9515: FixFieldDefinition(9515, "OptionDate", "LOCALMKTDATE", "FX Time Option end date."),
    640: FixFieldDefinition(
        640,
        "Price2",
        "PRICE",
        "FX Swap: price set in the order for the far leg (standard FIX Price2; "
        "absent from the bundled FIX44.xml, so defined here for 360T).",
    ),
    1903: FixFieldDefinition(
        1903, "RegulatoryTradeID", "STRING", "Regulatory trade identifier (TVTIC / USI / UTI)."
    ),
    1905: FixFieldDefinition(
        1905, "RegulatoryTradeIDSource", "STRING", "Indicates SEF; contains the 360T USI prefix."
    ),
    1906: FixFieldDefinition(
        1906,
        "RegulatoryTradeIDType",
        "INT",
        "Type of regulatory ID.",
        {
            "0": "Current (SEF/EMIR)",
            "3": "Related (Complex Trade Component ID)",
            "5": "Trading venue transaction identifier (TVTIC)",
        },
    ),
    1907: FixFieldDefinition(
        1907, "NoRegulatoryTradeIDs", "NUMINGROUP", "Number of regulatory trade ID entries."
    ),
    2411: FixFieldDefinition(
        2411, "RegulatoryLegRefID", "STRING", "Links a regulatory ID to a swap leg (LegRefID)."
    ),
    2384: FixFieldDefinition(
        2384,
        "NestedPartyRoleQualifier",
        "INT",
        "Nested party role qualifier.",
        {"22": "Algorithm", "24": "Natural person"},
    ),
}

# Standard tags 360T assigns venue-specific or extended enum values to. Merged
# over the default dict (venue values win on conflict, standard values retained).
_360T_ENUM_EXTENSIONS: dict[int, dict[str, str]] = {
    537: {"0": "Indicative (market data request; not tradeable)", "1": "Tradeable"},
    298: {"1": "Cancel for Symbol", "4": "Cancel all quotes for the request"},
    658: {"99": "Other"},
    380: {
        "0": "Other",
        "3": "Unsupported message type",
        "5": "Conditionally required field missing",
    },
    40: {
        "D": "Previously quoted",
        "1": "Market order",
        "2": "Limit order (FX Spot and Forward only)",
    },
    54: {"1": "Buy", "2": "Sell", "B": "As Defined (block trades; matches netted leg side)"},
    29: {
        "1": "AOTC (any other capacity)",
        "3": "MTCH (matched principal)",
        "4": "DEAL (dealing on own account)",
    },
    452: {
        "1": "Executing Firm",
        "4": "Clearing Firm",
        "12": "Executing Trader",
        "35": "Liquidity Provider",
        "63": "Systematic Internaliser (SI)",
        "64": "Multilateral Trading Facility (MTF)",
        "78": "Allocation Entity",
        "116": "Reporting Party",
        "122": "Investment decision maker",
    },
    447: {
        "D": "Proprietary custom code",
        "G": "MIC",
        "N": "Legal Entity Identifier",
        "P": "Short code identifier",
    },
    828: {"65": "TPAC (Package Trade)"},
    2670: {
        "0": "No preceding order in book (price within avg spread of liquid instrument)",
        "1": "No preceding order in book (price from system reference for illiquid instrument)",
        "2": "No preceding order in book (price subject to conditions other than market price)",
        "3": "No public price for preceding order (public reference used for matching)",
        "4": "No public price quoted (instrument illiquid)",
        "5": "No public price quoted (size)",
        "9": "No public price and/or size quoted (large in scale)",
    },
}


class ThreeSixtyTHandler(VenueHandler):
    """Handler for 360T RFS Market Taker FIX messages."""

    @property
    def name(self) -> str:
        return "360T RFS"

    @property
    def sender_comp_ids(self) -> list[str]:
        # Real RFS sessions use client-specific agreed CompIDs; detection is
        # best-effort. (UAT.ATP.RFS.MKT belongs to Smart Trade, not 360T.)
        return ["360T", "THREESIXTYT", "360TGTX"]

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        return list(_360T_CUSTOM_TAGS.values())

    @property
    def enum_extensions(self) -> dict[int, dict[str, str]]:
        return _360T_ENUM_EXTENSIONS

    # -- Enrichment -------------------------------------------------------

    def enhance_message(self, message: FixMessage) -> FixMessage:
        message = super().enhance_message(message)
        product = self._derive_product_type(message)
        if product:
            message.product_type = product
        for tag, key in ((7611, "execution_venue_type"), (7653, "uti"), (7654, "uti_far")):
            value = message.get_value(tag)
            if value:
                message.venue_extras[key] = value
        return message

    # Message types that carry a tradeable product (QuoteRequest, Quote,
    # NewOrderSingle, NewOrderMultileg, ExecutionReport). Administrative
    # messages (News/QuoteCancel/QuoteRequestReject/BusinessMessageReject/
    # SecurityDefinition(Request)) have no product.
    _PRODUCT_MSG_TYPES = frozenset({"R", "S", "D", "AB", "8"})

    @staticmethod
    def _has_far_leg(message: FixMessage) -> bool:
        """Whether a 360T message carries a far swap leg.

        SettlDate2(193) is present on swap orders/executions; the Quote message
        carries no 193 and instead has far-leg prices 6050/6051 and far size
        OrderQty2(192). NoLegs(555) on a 360T Quote denotes a *non-swap*
        multi-leg instrument, so it is deliberately not a swap signal. Both
        ``_derive_product_type`` and ``_refine_swap_quote`` use this predicate so
        ``product_type`` and ``trade.is_swap`` can never disagree.
        """
        return bool(
            message.get_value(193)
            or message.get_value(192)
            or message.get_value(6050)
            or message.get_value(6051)
        )

    @staticmethod
    def _derive_product_type(message: FixMessage) -> str | None:
        """Derive the product type from 360T field combinations.

        360T sends no SecurityType(167). Only the economic message types carry a
        product; administrative messages return None. Order matters: NDS before
        NDF before Swap. Forward vs Spot needs SettlDate(64); a tradeable Quote
        without 64 falls back to Spot.
        """
        if message.msg_type not in ThreeSixtyTHandler._PRODUCT_MSG_TYPES:
            return None
        if message.get_value(7071) == "FX-BT":
            return "Block Trade"
        if message.get_value(9515):
            return "FX Time Option"
        has_far = ThreeSixtyTHandler._has_far_leg(message)
        if message.get_value(7541) and has_far:
            return "NDS"
        if message.get_value(541) and not has_far:
            return "NDF"
        if has_far:
            return "Swap"
        settl = message.get_value(64)
        ref_spot = message.get_value(7070)
        if settl and ref_spot and settl != ref_spot:
            return "Forward"
        if message.get_value(7071) == "FX-STD" or settl:
            return "Spot"
        return None

    # -- Trade extraction -------------------------------------------------

    def extract_trade(self, message: FixMessage) -> ParsedTrade:
        trade = super().extract_trade(message)
        if trade.quantity is None:
            trade.quantity = _to_float(message.get_value(38))

        # Block trades carry independent legs, not a near/far swap. The base
        # handler flags is_swap on any >=2-leg message and fills swap economics
        # from those legs; clear them so a block is not mistaken for a swap.
        if message.get_value(7071) == "FX-BT":
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
            return trade

        if message.msg_type == "S":
            self._refine_swap_quote(message, trade)
        else:
            self._refine_swap_execution(message, trade)
        return trade

    def _refine_swap_execution(self, message: FixMessage, trade: ParsedTrade) -> None:
        """Apply 360T swap-execution economics on top of the base extraction."""
        if not trade.is_swap and self._has_far_leg(message):
            self._extract_swap_execution_info(message, trade, message.get_field(54), [])

        if not trade.is_swap:
            return

        base, term = parse_symbol(trade.symbol)
        side_code = message.get_value(54)
        # 360T Side(54) is relative to the base currency (ccy1), and for swaps
        # to the far leg. Reuse swap_side_actions with the base currency as the
        # "trade currency" so actions read e.g. "Buy EUR" / "Sell EUR".
        if base and side_code in ("1", "2"):
            near_action, far_action = swap_side_actions(side_code, base, base, term)
            trade.near_leg_action = near_action
            trade.far_leg_action = far_action
            trade.swap_side_source = "360t"

        # 360T carries the far-leg *executed* rate in 6160 (LastPx2); the base
        # handler reads 640 (the order price). Prefer the executed rate.
        far_exec = _to_float(message.get_value(6160))
        if far_exec is not None:
            trade.far_leg_price = far_exec
            if trade.near_leg_price is not None:
                trade.swap_points = far_exec - trade.near_leg_price
                ps = trade.pip_size or pip_size(trade.symbol)
                if ps:
                    trade.swap_points_pips = trade.swap_points / ps

    def _refine_swap_quote(self, message: FixMessage, trade: ParsedTrade) -> None:
        """Detect and populate a 360T swap quote.

        The base handler only flags a swap when SettlDate2(193) is present, which
        a 360T Quote never carries; detect via the far-leg signals instead (the
        same predicate ``_derive_product_type`` uses). A 360T swap Quote carries
        no far settlement date (no 193; NoLegs is non-swap), so that field is
        left as set by the base handler.
        """
        if not self._has_far_leg(message):
            return  # not a swap quote

        trade.is_swap = True
        near_bid = _to_float(message.get_value(132))
        near_offer = _to_float(message.get_value(133))
        bid_px2 = _to_float(message.get_value(6050))
        offer_px2 = _to_float(message.get_value(6051))
        trade.near_leg_bid_rate = near_bid
        trade.near_leg_offer_rate = near_offer
        trade.far_leg_bid_rate = bid_px2
        trade.far_leg_offer_rate = offer_px2
        trade.near_quantity = trade.quantity or _to_float(message.get_value(38))
        trade.far_quantity = _to_float(message.get_value(192))
        if bid_px2 is not None and near_bid is not None:
            trade.bid_swap_points = bid_px2 - near_bid
        if offer_px2 is not None and near_offer is not None:
            trade.offer_swap_points = offer_px2 - near_offer
