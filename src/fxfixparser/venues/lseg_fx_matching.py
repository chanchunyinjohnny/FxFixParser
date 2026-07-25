"""LSEG / Refinitiv FX Matching (MAPI) venue handler.

Supports the Matching API (MAPI) FIX interface for LSEG (formerly Refinitiv /
Thomson Reuters) FX Matching, the anonymous interbank central-limit-order-book
("Matching") venue. Products are FX Spot (SecurityType=FXSPOT) and FX Forward
Swap (SecurityType=FXSWAP, Near/Far two-leg).

Written against the *LSEG FX Matching FIX Interface User Guide* v1.21
(20 March 2025).

The application layer is FIX 5.0 SP2 (with extension packs EP100/EP171) over a
FIXT 1.1 session layer. The session negotiates DefaultApplVerID(1137)=9 at
Logon; ApplVerID(1128)=9 is optional per message (the Chapter-5 header table
marks it "not required") but is normally present, and when it is the bundled
``spec/FIX50SP2.xml`` is auto-loaded by the parser so the entire standard tag
space decodes without help. This handler adds the MAPI-specific layer:

* MAPI User-Defined Fields (LockedStatus 5007, the MiFID-II MTF-forward fields
  TR_TradingCapacity 31344 / TR_Npft 31345, OrdersLockFilter 20020).
* One venue-scoped tag-number *override*: the TradeCaptureReport (35=AE)
  overloads tag 1056, carrying the swap's spot reference rate there instead of
  the standard CalculatedCcyLastQty. ``custom_tags`` replaces the definition
  only while this venue is active, so other venues keep the standard meaning
  (the same per-venue isolation Bloomberg DOR / SGX Titan OTC rely on).
* Enum subsets MAPI assigns venue-specific meaning to (SecurityType FXSWAP =
  "FX Forward Swap", PriceType 20/21 = Normal/Inverse, ExecType F/I =
  hard/soft match, the quote-negotiation and party/settlement enums, etc.).
* Two MAPI quantity/price conventions the shared extraction cannot guess:
  every quantity is in units of ContractMultiplier(231) = 1,000,000, and an
  FX Forward Swap is priced in *swap points* via Price(44) rather than an
  all-in rate. See :meth:`LSEGFXMatchingHandler.extract_trade`.

Everything else MAPI sends is standard FIX 5.0 SP2 and decodes from the bundled
spec — in particular, bilateral credit travels in the NoLimitAmts(1630) group as
LastLimitAmt(1632) / LimitAmtRemaining(1633), and the per-leg calculated
quoted-currency quantity is LegCalculatedCcyLastQty(1074).

Credit / Prime-Broker-Client admin messages (U1/U2/U3, PartyAction*) are
*labelled* (their MsgTypes and field names decode) but their body structure is
not modelled — see the design doc for scope.

Venue custom tags are defined in Python (no runtime XML), per the project's
proprietary-data policy. See
``docs/plans/2026-06-04-lseg-fx-matching-support-design.md``.
"""

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.core.fx_math import parse_symbol, pip_size
from fxfixparser.core.message import FixMessage, ParsedTrade
from fxfixparser.venues.base import VenueHandler

# ContractMultiplier(231) is "Always 1000000" on MAPI; used when a message
# omits the tag (it is conditional on the Pending-Cancel / Pending-Replace
# ExecutionReports and absent from the quote-negotiation messages).
_MAPI_CONTRACT_MULTIPLIER = 1_000_000.0

# The forward-swap quote-negotiation pair. Quote(S) proposes, QuoteResponse(AJ)
# hits/counters/passes; both carry the amounts under negotiation.
_NEGOTIATION_MSG_TYPES = frozenset({"S", "AJ"})

# ---------------------------------------------------------------------------
# Custom tag definitions
# ---------------------------------------------------------------------------
_LSEG_CUSTOM_TAGS: dict[int, FixFieldDefinition] = {
    # --- MAPI User-Defined Fields used on trade / quote / mass-action ---
    5007: FixFieldDefinition(
        5007,
        "LockedStatus",
        "BOOLEAN",
        "FX Spot orders only (any order type except IOC): marks an order as "
        "locked, affecting how Mass Action Cancel (with OrdersLockFilter 20020) "
        "targets it. Set only at submission; defaults to N. Not allowed on FX "
        "Forward Swap or IOC.",
        {"Y": "Locked", "N": "Not locked (default)"},
    ),
    20020: FixFieldDefinition(
        20020,
        "OrdersLockFilter",
        "INT",
        "Whether locked orders are included in a mass cancel (MassActionType=3). "
        "Sent on OrderMassActionRequest(CA), echoed on OrderMassActionReport(BZ).",
        {
            "1": "Non-locked only (default)",
            "2": "Locked only",
            "3": "Both locked and non-locked",
        },
    ),
    31344: FixFieldDefinition(
        31344,
        "TR_TradingCapacity",
        "INT",
        "MiFID II (MTF forwards) trading capacity of the executing firm on "
        "FXSWAP. Mandatory on ExecutionReport/TradeCaptureReport from Matching "
        "1.7; defaulted to 1 (DEAL) if absent on entry. Only value 1 is used.",
        {
            "1": "DEAL (dealing on own account)",
            "MTCH": "Matched principal (FIX-defined, not used by Matching)",
            "AOTC": "Any other capacity (FIX-defined, not used by Matching)",
        },
    ),
    31345: FixFieldDefinition(
        31345,
        "TR_Npft",
        "BOOLEAN",
        "MiFID II (MTF forwards) Non Price-Forming Transaction flag on FXSWAP "
        "(securities financing, clearing/settlement-only, or portfolio "
        "compression). Optional on NewOrderSingle(D) entry, defaulting to N; "
        "conditionally required on ExecutionReport(8) and inside the "
        "TradeCaptureReport(AE) NoSides group, echoed back or defaulted.",
        {
            "Y": "Non Price Forming Trade",
            "N": "Not a Non Price Forming Trade (default)",
        },
    ),
    # --- Venue-scoped override: MAPI reuses this standard tag number ---
    1056: FixFieldDefinition(
        1056,
        "CalculatedCcyLastQty",
        "PRICE",
        "TradeCaptureReport(35=AE) only, resolved by SecurityType(167): FXSWAP "
        "=> LastSpotRate (the swap's spot reference rate); FXSPOT => "
        "CalculatedCcyLastQty (calculated quoted-currency quantity, already "
        "multiplied by ContractMultiplier(231)). The ExecutionReport(35=8) "
        "carries the swap spot reference in the standard LastSpotRate(194).",
    ),
    # --- Credit / PBC admin UDFs: labelling only (bodies out of scope) ---
    20003: FixFieldDefinition(
        20003,
        "MaxOpenOrdersPerInstrument",
        "INT",
        "PBC credit admin: new Maximum Open Orders Per Instrument (MOOPI) limit, "
        "valid 1-200. Used on PartyActionRequest(DH), U1, and the U3 NoPBCs group.",
    ),
    20005: FixFieldDefinition(
        20005,
        "PbcUpdateResultStatus",
        "INT",
        "PBC credit admin (U2): result of a Prime-Broker-Client limit update.",
        {
            "0": "Success",
            "1": "Fail Value Too Large",
            "2": "Fail Value Too Small",
            "3": "Credit entity not found for Prime Broker",
            "4": "Invalid prime broker",
            "5": "Invalid prime broker client",
            "6": "PBC does not belong to PB",
            "7": "Global permission required",
            "8": "Local permission required",
            "9": "Credit entity not found for Prime Broker client",
            "10": "Inconsistent updates for MAPI",
            "11": "Invalid MCA state",
            "12": "Invalid max open orders per instrument",
            "13": "Invalid Request",
            "14": "Permission denied",
            "15": "Fail others",
            "16": "unknown",
        },
    ),
    20006: FixFieldDefinition(
        20006,
        "DOMCAD",
        "BOOLEAN",
        "PBC credit admin (U3): true if the PB Credit Admin being not-logged-in "
        "would prevent the party from trading.",
        {"Y": "True", "N": "False"},
    ),
    20009: FixFieldDefinition(
        20009,
        "NoPBCs",
        "NUMINGROUP",
        "PBC credit admin (U3): count of Prime Broker Clients covered by the "
        "party-status report.",
    ),
    20010: FixFieldDefinition(
        20010,
        "BranchStatus",
        "INT",
        "PBC credit admin (U3 NoPBCs group): trading status of the branch/PBC.",
        {"1": "Enabled", "2": "Disabled", "3": "Inhibited"},
    ),
    20011: FixFieldDefinition(
        20011,
        "CreditAdminStatus",
        "INT",
        "PBC credit admin (U3 NoPBCs group): Prime Broker Credit Admin login status.",
        {"1": "PB CA is logged in", "2": "PB CA is not logged in"},
    ),
    20012: FixFieldDefinition(
        20012,
        "PBCID",
        "STRING",
        "PBC credit admin (U3 NoPBCs group): PBC identifier, format <TCID>*<Answerback>.",
    ),
    20013: FixFieldDefinition(
        20013,
        "PartyStatusRptID",
        "STRING",
        "PBC credit admin (U3): identifier for the party-status report.",
    ),
}

# ---------------------------------------------------------------------------
# Enum extensions: standard tags MAPI assigns venue-specific values to.
# Merged over the FIX 5.0 SP2 values (venue wins on key conflicts), so standard
# codes remain and MAPI's relabels/additions apply.
# ---------------------------------------------------------------------------
_LSEG_ENUM_EXTENSIONS: dict[int, dict[str, str]] = {
    # --- Detection / session ---
    56: {"TR MATCHING": "MAPI gateway (always this literal) - venue signature"},
    57: {"FXM": "FX Matching (always this literal) - venue signature"},
    35: {
        "U1": "PBC Limit Update Request (MAPI custom)",
        "U2": "PBC Limit Update Response (MAPI custom)",
        "U3": "PBC Party Status Notification (MAPI custom)",
    },
    1407: {"100": "EP100 extension", "171": "EP171 (PBC session control)"},
    # --- Order / execution ---
    18: {
        "0": "Stay on offerside (FX price-side peg, OrderCancelReplaceRequest)",
        "9": "Stay on bidside (FX price-side peg)",
    },
    39: {
        "0": "New",
        "1": "Partially Filled",
        "2": "Filled",
        "4": "Cancelled",
        "6": "Pending Cancel",
        "7": "Stopped",
        "8": "Rejected",
        "9": "Suspended",
        "C": "Expired (GTD/GFT)",
        "E": "Pending Replace",
    },
    40: {"2": "Limit (the only OrdType supported by Matching)"},
    54: {
        "1": "Buy (from volume-currency perspective)",
        "2": "Sell (from volume-currency perspective)",
    },
    59: {
        "0": "Day / Standard Order (default)",
        "3": "Immediate or Cancel (IOC)",
        "6": "Good Till Date (GTD, with ExpireTime 126)",
        "A": "Good For Time (GFT, with ExposureDuration 1629)",
    },
    150: {
        "0": "New",
        "4": "Cancelled",
        "5": "Replaced",
        "6": "Pending Cancel",
        "8": "Rejected",
        "9": "Suspended (Hold)",
        "C": "Expired (GTD/GFT)",
        "D": "Restated",
        "E": "Pending Replace",
        "F": "Trade (hard match)",
        "I": "Order Status (soft match)",
        "L": "Triggered/Activated by System (Release)",
    },
    167: {"FXSPOT": "FX Spot", "FXSWAP": "FX Forward Swap (Near/Far two-leg)"},
    423: {
        "20": "Normal (units of ccy2 per 1 ccy1; volume ccy = base)",
        "21": "Inverse (units of ccy1 per 1 ccy2; volume ccy = quoted)",
    },
    847: {"1001": "Matching Iceberg (MAPI user-defined)"},
    1028: {
        "Y": "Order entered by a manual user",
        "N": "Order entered by an algorithm",
    },
    1057: {
        "Y": "This order/side was the aggressor",
        "N": "This order/side was passive (standing in the book)",
    },
    # --- Cancel / reject ---
    102: {"0": "Too Late to Cancel (also unknown order ID)", "99": "Other"},
    103: {
        "1": "Unknown Symbol",
        "11": "Unsupported Order Characteristic",
        "13": "Incorrect Quantity",
        "99": "Other",
    },
    127: {
        "A": "Unknown Symbol",
        "B": "Wrong Side",
        "C": "Quantity Exceeds Order",
        "D": "No Matching Order",
        "E": "Price Exceeds Limit",
        "F": "Calculation Difference",
        "Z": "Other",
    },
    378: {
        "5": "Partial decline of OrderQty (remaining below minimum)",
        "6": "Cancel on Trading Halt",
        "12": "Cancel on Connection Loss",
        "13": "Cancel on Logout",
        "99": "Other",
    },
    380: {
        "0": "Other",
        "3": "Unknown / Unsupported Message Type",
        "4": "Application Not Available",
        "5": "Conditionally required tag missing",
        "6": "Not Authorized",
        "7": "DeliverToFirm Not available at this time",
    },
    434: {"1": "Order Cancel Request", "2": "Order Cancel/Replace Request"},
    373: {
        "0": "Invalid Tag Number",
        "1": "Required Tag Missing",
        "2": "Tag not defined for this message type",
        "3": "Undefined tag",
        "4": "Tag specified without a value",
        "5": "Value is incorrect (out of range) for this tag",
        "6": "Incorrect data format for value",
        "9": "CompID problem",
        "10": "SendingTime Accuracy Problem",
        "11": "Invalid MsgType",
        "12": "XML Validation Error",
        "13": "Tag appears more than once",
        "14": "Tag specified out of required order",
        "15": "Repeating group fields out of order",
        "16": "Incorrect NumInGroup count for repeating group",
        "17": "Non Data value includes field delimiter",
        "18": "Invalid/Unsupported Application Version",
        "99": "Other",
    },
    # --- Mass action ---
    1373: {"1": "Suspend/Hold", "2": "Release", "3": "Cancel orders"},
    1374: {
        "1": "All orders for a security/instrument",
        "5": "All orders for a SecurityType / asset class",
        "7": "All orders",
    },
    1375: {"0": "Rejected", "1": "Accepted"},
    1376: {
        "0": "Mass Action Not Supported",
        "1": "Invalid or unknown security",
        "5": "Invalid or unknown Security Type",
        "99": "Other",
    },
    # --- Quote negotiation (forward swap) ---
    297: {
        "0": "Accepted",
        "5": "Rejected (e.g. max proposal requests exceeded)",
        "8": "Query (Bell notification to counterparty)",
        "16": "Active",
        "17": "Cancelled (No-Deal / auto-No-Deal / abnormal termination)",
    },
    300: {"99": "Other (e.g. max number of proposal requests exceeded)"},
    537: {"0": "Indicative", "3": "Counter"},
    694: {"1": "Hit/Lift", "2": "Counter", "6": "Pass (No-Deal)"},
    233: {
        "TEXT": "Free-form text (no-deal finalisation body)",
        "MAXORDQTY": "Maximum Order Size (Quote negotiation stipulation)",
    },
    234: {
        "Inhibit workflow required": "Send PartyActionRequest(DH) inhibit to terminate proposal",
        "Reposition workflow required": "Send OrderCancelReplace(G) reposition or OrderCancel(F)",
        "None": "No further Inhibit/Reposition action required",
    },
    394: {"1": "Non Disclosed style"},
    1385: {
        "5": "Bid and Offer (two or more sides)",
        "6": "Bid and Offer OCO (one auto-cancelled when the other fully trades)",
    },
    # --- List ---
    429: {"1": "Ack", "2": "Response"},
    431: {"4": "Cancelling", "6": "All Done", "7": "Reject"},
    1386: {"5": "Unknown Order", "11": "Unsupported Order Characteristic", "99": "Other"},
    # --- Parties / settlement / structure ---
    447: {"C": "Generally accepted market participant identifier (Answerback)"},
    452: {
        "13": "Order Origination Firm (this party / report owner)",
        "53": "Trader mnemonic",
        "56": "Acceptable Counterparty",
        "3": "Client ID",
    },
    803: {
        "2": "Person (trader user ID / login name)",
        "25": "Location Desk (TCID - master dealing code)",
    },
    1118: {"C": "Generally accepted market participant identifier (Answerback)"},
    1119: {
        "13": "Order Origination Firm (this organisation / report owner)",
        "56": "Acceptable Counterparty",
    },
    1122: {
        "2": "Person (trader's username / login name)",
        "25": "Location Desk (TCID)",
    },
    783: {"C": "Generally accepted market participant identifier"},
    784: {
        "27": "Buyer/Seller (Receiver/Deliverer) - non-CLS trades",
        "86": "CLS Member Bank - trade marked for CLS settlement",
    },
    786: {"16": "BIC / SWIFT Code"},
    1164: {"4": "Buyer's settlement instructions", "5": "Seller's settlement instructions"},
    573: {
        "0": "Acknowledged / matched-affirmed (confirmed)",
        "1": "Unacknowledged / unmatched (unconfirmed but valid)",
    },
    624: {
        "1": "Buy (from volume-currency perspective)",
        "2": "Sell (from volume-currency perspective)",
    },
    654: {
        "Near": "Near leg of the FX Swap (1st NoLegs entry)",
        "Far": "Far leg of the FX Swap (2nd NoLegs entry)",
    },
    552: {
        "1": "One side - an FX Spot trade (always reported from the receiving user's perspective)",
        "2": "Two entries - the near and far legs of an FX Swap, not two counterparty sides",
    },
    1631: {
        "0": "Credit Limit (the value used by Matching)",
        "1": "Gross Position Limit",
        "2": "Net Position Limit",
        "3": "Risk Exposure Limit",
        "4": "Long Position Limit",
        "5": "Short Position Limit",
    },
    2594: {"2": "Liquidity provision activity order (MiFID II market-making)"},
    2595: {"Y": "True", "N": "False (default)"},
    # --- Trade-report constants (legibility) ---
    325: {"Y": "Sent unsolicited / from a subscription (always Y on TCRs)"},
    487: {"0": "New (trade cancellations not supported)"},
    828: {"54": "OTC Trade"},
    854: {"1": "Contracts"},
    856: {"2": "Accept"},
    # --- Party action (labelling) ---
    2329: {
        "0": "Suspend (inhibit)",
        "1": "Halt Trading (disable)",
        "2": "Reinstate (uninhibit / enable)",
    },
    2332: {"0": "Accepted (pending)", "1": "Completed", "2": "Rejected"},
    2333: {
        "0": "Invalid Party",
        "1": "Unknown Requesting Party",
        "98": "Not Authorised",
        "99": "Other",
    },
    1547: {
        "FXSPOT": "PBC Session Control workflow",
        "FXSWAP": "Swap inhibit workflow (default)",
    },
    # --- Strategy parameters (Iceberg) ---
    958: {
        "T": "Tip Specification Type",
        "Q1": "1st (primary) tip quantity",
        "Q2": "2nd tip quantity",
        "Q3": "3rd tip quantity",
        "Qmin": "Minimum random tip",
        "Qmax": "Maximum random tip",
        "D": "Delay (no delay if absent)",
    },
    960: {"D": "Defined (when Name=T)", "R": "Random (when Name=T)"},
}


def _to_float(value: str | None) -> float | None:
    """Parse a tag value as float, returning None on missing / invalid."""
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _leg_entries(message: FixMessage) -> list[dict[str, str]]:
    """Return the NoLegs (555) group entries as {tag_str: value} dicts."""
    for sf in message.get_structured_fields():
        if sf.is_group and sf.group and sf.group.count_field.tag == 555:
            return [{str(f.tag): f.raw_value for f in entry.fields} for entry in sf.group.entries]
    return []


class LSEGFXMatchingHandler(VenueHandler):
    """Handler for LSEG / Refinitiv FX Matching (MAPI) FIX messages."""

    @property
    def name(self) -> str:
        return "LSEG FX Matching"

    @property
    def sender_comp_ids(self) -> list[str]:
        # No fixed venue-side SenderCompID exists - client CompIDs are per-firm
        # Refinitiv-issued credentials (4-letter TCID + digits). The MAPI gateway
        # CompID is always "TR MATCHING": it appears as TargetCompID(56) on
        # client->MAPI messages and SenderCompID(49) on MAPI->client messages.
        # VenueRegistry.detect_from_message checks tags 49/56/115, so listing it
        # here resolves both directions without an interface change.
        return ["TR MATCHING", "TRMATCHING", "TR_MATCHING"]

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        return list(_LSEG_CUSTOM_TAGS.values())

    @property
    def enum_extensions(self) -> dict[int, dict[str, str]]:
        return _LSEG_ENUM_EXTENSIONS

    def enhance_message(self, message: FixMessage) -> FixMessage:
        message = super().enhance_message(message)
        match_id = message.get_value(880)  # TrdMatchID
        if match_id:
            message.venue_extras["match_id"] = match_id
        counterparty = self._counterparty(message)
        if counterparty:
            message.venue_extras["counterparty"] = counterparty
        # The Quote(S)/QuoteResponse(AJ) negotiation cluster exists only for FX
        # Forward Swaps, but carries no SecurityType(167) for the generic
        # product detection to key off, so name the product here.
        if message.msg_type in _NEGOTIATION_MSG_TYPES:
            message.product_type = "Swap"
        return message

    def extract_trade(self, message: FixMessage) -> ParsedTrade:
        trade = super().extract_trade(message)

        # OrderID may be the literal "NONE" on MAPI.
        if trade.order_id == "NONE":
            trade.order_id = None

        # ExecID(17) is non-unique on MAPI (shared across all reports from one
        # event). Prefer SecondaryExecID(527), then TradeID(1003) on a TCR.
        trade.exec_id = message.get_value(527) or message.get_value(1003) or message.get_value(17)

        # The TradeCaptureReport overloads tag 1056 as the swap spot reference
        # rate (the ExecutionReport uses the standard LastSpotRate(194)). When
        # 194 is absent the base handler falls back to the near leg price; 1056
        # is the venue's own spot reference, so prefer it.
        if trade.is_swap and message.get_value(167) == "FXSWAP" and not message.get_value(194):
            spot_1056 = _to_float(message.get_value(1056))
            if spot_1056 is not None:
                trade.spot_rate = spot_1056

        self._apply_swap_price_semantics(message, trade)
        self._extract_negotiated_quantities(message, trade)
        self._apply_contract_multiplier(message, trade)

        return trade

    @staticmethod
    def _apply_swap_price_semantics(message: FixMessage, trade: ParsedTrade) -> None:
        """Reconcile MAPI's swap-points pricing with ``ParsedTrade.price``.

        MAPI prices an FX Forward Swap in *swap points*, not an all-in rate:
        Price(44) "specifies the swap points not the all-in rate" and the
        ExecutionReport echoes it back unchanged, while LastPx(31) is sent only
        for SecurityType(167)=FXSPOT. The shared ``31 or 44`` fallback would
        therefore leave swap points sitting in ``trade.price`` on every FXSWAP
        order and non-match execution report.

        Leg-less FXSWAP messages (NewOrderSingle, ExecutionReports whose
        ExecType is not F/I) also defeat the shared swap detection: MAPI never
        sends the side-by-side 192/193 shape and only populates NoLegs(555) on
        match reports. Flag those as swaps here.
        """
        if message.get_value(167) != "FXSWAP":
            return

        if not trade.is_swap:
            trade.is_swap = True
            base_ccy, term_ccy = parse_symbol(trade.symbol)
            trade.base_currency = trade.base_currency or base_ccy
            trade.term_currency = trade.term_currency or term_ccy
            trade.trade_currency = trade.trade_currency or message.get_value(15)

        # LastPx(31) present means a genuine rate (on the TradeCaptureReport it
        # is the all-in price of the far leg), so leave trade.price alone.
        if message.get_value(31) is not None:
            return

        points = _to_float(message.get_value(44))
        if points is None:
            return
        if trade.swap_points is None:
            trade.swap_points = points
            ps = pip_size(trade.symbol)
            trade.pip_size = ps
            if ps:
                trade.swap_points_pips = points / ps
        # Never let the raw points masquerade as a rate. Where the legs are
        # present, follow MAPI's own convention for LastPx on the swap
        # TradeCaptureReport: the all-in price of the far leg.
        trade.price = trade.far_leg_price

    @staticmethod
    def _extract_negotiated_quantities(message: FixMessage, trade: ParsedTrade) -> None:
        """Pull the negotiated amounts out of a Quote(S) / QuoteResponse(AJ).

        The forward-swap negotiation messages carry no SecurityType(167), no
        bid/offer sizes and no settlement dates — the amounts under negotiation
        are OrderQty(38) at message level and LegOrderQty(685) per leg, keyed by
        LegRefID(654) = Near/Far. The shared quote extraction reads none of
        those, so a MAPI negotiation would otherwise surface no quantity at all.
        """
        if message.msg_type not in _NEGOTIATION_MSG_TYPES:
            return

        trade.is_swap = True
        base_ccy, term_ccy = parse_symbol(trade.symbol)
        trade.base_currency = trade.base_currency or base_ccy
        trade.term_currency = trade.term_currency or term_ccy
        if trade.quantity is None:
            trade.quantity = _to_float(message.get_value(38))

        legs = _leg_entries(message)
        if len(legs) < 2:
            return
        by_ref = {(leg.get("654") or "").lower(): leg for leg in legs}
        near = by_ref.get("near", legs[0])
        far = by_ref.get("far", legs[-1])
        trade.near_quantity = _to_float(near.get("685"))
        trade.far_quantity = _to_float(far.get("685"))

    @staticmethod
    def _apply_contract_multiplier(message: FixMessage, trade: ParsedTrade) -> None:
        """Scale MAPI's contract quantities into real notional amounts.

        ContractMultiplier(231) is "Always 1000000" and "unless otherwise
        specified all quantity related fields will be implicitly multiplied by
        this amount" — OrderQty(38)=1 means 1,000,000, and instruments with
        smaller lot sizes send fractions (0.1 = 100,000). Chapter 7 repeats it
        for LastQty. Without this every MAPI amount would read a million times
        too small next to the other venues.

        Only the raw contract quantities are scaled: CalculatedCcyLastQty(1056)
        and LegCalculatedCcyLastQty(1074) are already multiplied at source, and
        the credit amounts in the NoLimitAmts(1630) group are separately
        documented as whole millions and are not surfaced on ParsedTrade.
        """
        multiplier = _to_float(message.get_value(231)) or _MAPI_CONTRACT_MULTIPLIER
        if multiplier == 1.0:
            return
        for attr in ("quantity", "near_quantity", "far_quantity"):
            value = getattr(trade, attr, None)
            if value is not None:
                setattr(trade, attr, value * multiplier)

    @staticmethod
    def _counterparty(message: FixMessage) -> str | None:
        """Return the counterparty answerback: the PartyID / RootPartyID whose
        role is 56 (Acceptable Counterparty).

        Pairs each role-56 marker with the most recent ID tag in the flat field
        list. Sufficient for the single-entry counterparty groups MAPI emits on
        ExecutionReport (Parties 453) and TradeCaptureReport (RootParties 1116).
        """
        for id_tag, role_tag in ((448, 452), (1117, 1119)):
            pending_id: str | None = None
            for f in message.fields:
                if f.tag == id_tag:
                    pending_id = f.raw_value
                elif f.tag == role_tag and f.raw_value == "56":
                    if pending_id:
                        return pending_id
        return None
