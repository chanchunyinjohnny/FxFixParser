"""Bloomberg DOR (Derivatives Order Routing) venue handler.

Supports Bloomberg's ORP/DOR FIX protocol for FX trading including
Spot, Forward, Swap, NDF, and FX Algo orders.

Bloomberg-specific custom tags are defined in Python below.
Standard FIX tags are already provided by the bundled FIX44.xml spec.
"""

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.core.message import FixMessage
from fxfixparser.venues.base import VenueHandler

# CompIDs that identify Bloomberg traffic — the FXGO platform plus the DOR/ORP
# routing protocol. Used to scope protocol-aware detection so Bloomberg DOR never
# claims another venue's FIXT.1.1 / FIX 5.0 messages.
_BLOOMBERG_COMP_IDS = {
    "FXGO",
    "BLOOMBERG",
    "BBG",
    "BFXGO",
    "BLOOMBERG_DOR",
    "BBGDOR",
    "DOR",
    "FXOM",
    "ORP",
}

# Routing CompIDs that appear on OnBehalfOfCompID (115) / DeliverToCompID (128)
# for ORP/DOR order routing.
_DOR_ROUTING_IDS = {"DOR", "FXOM", "ORP", "BLOOMBERG_DOR", "BBGDOR"}

# Bloomberg MAP gateway sessions carry the ORP/DOR dialect over plain FIX 4.4
# with MAP_<party>[_<env>] CompIDs. The Bloomberg-side CompID always starts
# with MAP_BLP (BLP = Bloomberg L.P.), e.g. MAP_BLP_BETA in UAT.
_MAP_BLOOMBERG_PREFIX = "MAP_BLP"

# Bloomberg DOR custom tag definitions for FX-specific fields.
# Standard FIX tags (e.g. 8, 35, 55, 167) are covered by FIX44.xml.
_BLOOMBERG_CUSTOM_TAGS: dict[int, FixFieldDefinition] = {
    22913: FixFieldDefinition(
        tag=22913,
        name="LastMktSpotRate",
        field_type="PRICE",
        description="FX Algo: Prevailing market spot rate at the time of fill.",
    ),
    22914: FixFieldDefinition(
        tag=22914,
        name="AvgMktSpotRate",
        field_type="PRICE",
        description="FX Algo: Average prevailing market spot rate across all fills.",
    ),
    2793: FixFieldDefinition(
        tag=2793,
        name="AvgSpotRate",
        field_type="PRICE",
        description="FX Algo: Average all-in spot rate of all fills.",
    ),
    2794: FixFieldDefinition(
        tag=2794,
        name="AvgForwardPoints",
        field_type="PRICEOFFSET",
        description="FX Algo: Average forward points of all fills.",
    ),
    9032: FixFieldDefinition(
        tag=9032,
        name="AvgCommission",
        field_type="AMT",
        description="FX Algo: Total average commission across all fills.",
    ),
    22858: FixFieldDefinition(
        tag=22858,
        name="AlgoStrategyID",
        field_type="STRING",
        description="FX Algo: Bloomberg internal identifier for the algorithm strategy.",
    ),
    6215: FixFieldDefinition(
        tag=6215,
        name="Tenor",
        field_type="TENOR",
        description="FX tenor code (e.g., SP for Spot, 1W, 1M, 3M, 1Y).",
    ),
    22010: FixFieldDefinition(
        tag=22010,
        name="LegTenor",
        field_type="TENOR",
        description="FX Swap: Tenor code for the individual leg.",
    ),
    22262: FixFieldDefinition(
        tag=22262,
        name="CalculatedCurrency",
        field_type="CURRENCY",
        description="Currency opposite to the dealt currency.",
    ),
    22263: FixFieldDefinition(
        tag=22263,
        name="LegCalculatedCurrency",
        field_type="CURRENCY",
        description="Leg-level currency opposite to the dealt currency.",
    ),
    1071: FixFieldDefinition(
        tag=1071,
        name="LastSwapPoints",
        field_type="PRICEOFFSET",
        description="FX Swap: Swap points differential.",
    ),
    22869: FixFieldDefinition(
        tag=22869,
        name="ForexAccommodationTransaction",
        field_type="BOOLEAN",
        description="Indicates if the trade is an FX accommodation transaction.",
    ),
    9575: FixFieldDefinition(
        tag=9575,
        name="StagedOrderIsInquiry",
        field_type="BOOLEAN",
        description="Distinguishes staged orders from inquiries.",
    ),
    # Quote negotiation identifiers, carried on Quote (35=S), QuoteResponse
    # (35=AJ) and QuoteStatusReport (35=AI). SecondaryQuoteID(1751) and
    # RejectText(1328) are standard FIX 5.0 fields Bloomberg adds to these
    # messages; neither is in the bundled FIX 4.4 dictionary.
    1751: FixFieldDefinition(
        tag=1751,
        name="SecondaryQuoteID",
        field_type="STRING",
        description=(
            "Bloomberg trade key for the transaction. Returned on "
            "QuoteStatusReport (35=AI) when QuoteStatus(297)=0 (Accepted), and "
            "usable on the Bloomberg Terminal to view further trade details."
        ),
    ),
    1328: FixFieldDefinition(
        tag=1328,
        name="RejectText",
        field_type="STRING",
        description="Plain-text reject reason, sent when QuoteRejectReason(300)=99 (Other).",
    ),
    22335: FixFieldDefinition(
        tag=22335,
        name="QuoteRespRefID",
        field_type="STRING",
        description=(
            "Reverses a QuoteResponse (35=AJ) hit/lift in the order-based model "
            "when the original message did not reference a QuoteID(117); refers "
            "to the QuoteRespID(693) being canceled. Fixed income only — the "
            "ORP 1.9.8 QuoteResponse table marks this field [FI], not [FX]."
        ),
    ),
    22923: FixFieldDefinition(
        tag=22923,
        name="ManualTicket",
        field_type="INT",
        description="Manual ticket indicator.",
        valid_values={"0": "No", "1": "Before venue", "2": "After venue"},
    ),
    22000: FixFieldDefinition(
        tag=22000,
        name="AutoConfirm",
        field_type="BOOLEAN",
        description="Whether the trade should be auto-confirmed.",
    ),
    1056: FixFieldDefinition(
        tag=1056,
        name="CalculatedCcyLastQty",
        field_type="QTY",
        description="Calculated quantity in the non-dealt currency.",
    ),
    22040: FixFieldDefinition(
        tag=22040,
        name="DV01",
        field_type="PRICE",
        description="Dollar Value of 01: interest rate risk measure.",
    ),
    22041: FixFieldDefinition(
        tag=22041,
        name="LegDV01",
        field_type="PRICE",
        description="Leg-level Dollar Value of 01.",
    ),
    9610: FixFieldDefinition(
        tag=9610,
        name="NoNotes",
        field_type="NUMINGROUP",
        description="Number of note entries in the Bloomberg Notes repeating group.",
    ),
    9612: FixFieldDefinition(
        tag=9612,
        name="NoteLabel",
        field_type="STRING",
        description="Label/title for a Bloomberg note entry.",
    ),
    9613: FixFieldDefinition(
        tag=9613,
        name="NoteText",
        field_type="STRING",
        description="Text content of a Bloomberg note entry.",
    ),
    22941: FixFieldDefinition(
        tag=22941,
        name="SideProtection",
        field_type="INT",
        description="Side intended by taker in RFM request.",
    ),
    9896: FixFieldDefinition(
        tag=9896,
        name="PricingNo",
        field_type="STRING",
        description="Client's TS PX number for quote routing.",
    ),
    2795: FixFieldDefinition(
        tag=2795,
        name="OffshoreIndicator",
        field_type="INT",
        description="Offshore indicator.",
        valid_values={"0": "Regular", "1": "Offshore", "2": "Onshore"},
    ),
    22159: FixFieldDefinition(
        tag=22159,
        name="Ccy1MarketType",
        field_type="CHAR",
        description="Market/deliverability type of currency 1 of the pair.",
        valid_values={
            "N": "Non-deliverable",
            "O": "Onshore",
            "R": "Regular / offshore",
        },
    ),
    22160: FixFieldDefinition(
        tag=22160,
        name="Ccy2MarketType",
        field_type="CHAR",
        description="Market/deliverability type of currency 2 of the pair.",
        valid_values={
            "N": "Non-deliverable",
            "O": "Onshore",
            "R": "Regular / offshore",
        },
    ),
    1300: FixFieldDefinition(
        tag=1300,
        name="MarketSegmentID",
        field_type="STRING",
        description="Bloomberg market segment / execution facility identifier.",
        valid_values={
            "BETP": "Electronic Trading Platform",
            "BGM": "Global Markets",
            "BMTF": "Multilateral Trading Facility",
            "BSEF": "Swaps Execution Facility",
            "BTBS": "Bloomberg Trade Book Singapore",
            "BTBU": "Bloomberg Trade Book United States",
            "BTFE": "Bloomberg Trading Facility Europe",
            "XCFE": "China Foreign Exchange Trade System",
            "XOFF": "Off Facility",
        },
    ),
    1788: FixFieldDefinition(
        tag=1788,
        name="LegID",
        field_type="STRING",
        description=(
            "Reference identifier for the leg, referred to by "
            "RegulatoryLegRefID (2411) and AllocLegRefID (2727). For FX "
            "swaps this is an ordinal: 1 = near leg, 2 = far leg."
        ),
    ),
    # Regulatory trade IDs (NoRegulatoryTradeIDs group + the flat package-level
    # copies MAP execution reports emit before the 1907 count).
    1903: FixFieldDefinition(
        tag=1903,
        name="RegulatoryTradeID",
        field_type="STRING",
        description=(
            "Regulatory trade identifier (UTI / USI / TVTIC) assigned to "
            "the trade or to an individual leg."
        ),
    ),
    1905: FixFieldDefinition(
        tag=1905,
        name="RegulatoryTradeIDSource",
        field_type="STRING",
        description=("Identifier (LEI) of the entity that generated the regulatory " "trade ID."),
    ),
    1906: FixFieldDefinition(
        tag=1906,
        name="RegulatoryTradeIDType",
        field_type="INT",
        description="The type of regulatory trade ID being reported.",
        valid_values={
            "0": "Current (default if not specified)",
            "1": "Previous (cleared trade / novation)",
            "2": "Block (when reporting an allocated subtrade)",
            "3": "Related (when reporting a mixed swap)",
            "5": "Trading venue transaction identifier (MiFID II TVTIC)",
            "6": "Report tracking number (EMIR Refit RTN)",
        },
    ),
    1907: FixFieldDefinition(
        tag=1907,
        name="NoRegulatoryTradeIDs",
        field_type="NUMINGROUP",
        description="Number of regulatory trade ID entries.",
    ),
    2411: FixFieldDefinition(
        tag=2411,
        name="RegulatoryLegRefID",
        field_type="STRING",
        description=(
            "For multi-leg trades sent as a single message: marks the "
            "regulatory trade ID entry as applying only to the leg whose "
            "LegID (1788) matches (1 = near leg, 2 = far leg)."
        ),
    ),
    2405: FixFieldDefinition(
        tag=2405,
        name="ExecMethod",
        field_type="INT",
        description="How the trade was executed.",
        valid_values={
            "0": "Unspecified",
            "1": "Manual",
            "2": "Automated",
            "3": "Voice brokered",
            "4000": "Process negotiated trade (Bloomberg PNT)",
        },
    ),
    22280: FixFieldDefinition(
        tag=22280,
        name="AllocationCount",
        field_type="INT",
        description="Count of trade allocations expected.",
    ),
    # Competing dealer quotes — CompDealerQuoteGrp (10009). On MAP execution
    # reports the group also carries reference-rate pseudo-dealers (e.g.
    # CompDealerID "MidRate" / "RefRate") with indicative quote type.
    10009: FixFieldDefinition(
        tag=10009,
        name="NoCompDealerQuotes",
        field_type="NUMINGROUP",
        description=("Number of competing/participating dealer quote entries being " "specified."),
    ),
    10010: FixFieldDefinition(
        tag=10010,
        name="CompDealerID",
        field_type="STRING",
        description="Dealer's Bloomberg broker code.",
    ),
    # Overrides the LFX 'IsSEFTrade' meaning of 10011 for Bloomberg messages.
    10011: FixFieldDefinition(
        tag=10011,
        name="CompDealerQuotePrice",
        field_type="PRICE",
        description=(
            "Dealer's quoted price; omitted if the dealer did not quote. "
            "For FX swaps: the near leg all-in swap price."
        ),
    ),
    22161: FixFieldDefinition(
        tag=22161,
        name="CompDealerQuotePriceLeg2",
        field_type="PRICE",
        description="For FX swaps: dealer's all-in quoted price for the far leg.",
    ),
    22162: FixFieldDefinition(
        tag=22162,
        name="CompDealerQuoteForwardPoints",
        field_type="PRICEOFFSET",
        description=(
            "Dealer's forward points for the quoted price (near leg for FX "
            "swaps), in decimal form (61.99 points = 0.006199); may be "
            "negative."
        ),
    ),
    22163: FixFieldDefinition(
        tag=22163,
        name="CompDealerQuoteSwapPoints",
        field_type="PRICEOFFSET",
        description="For FX swaps: dealer's quoted swap points, in decimal form.",
    ),
    22276: FixFieldDefinition(
        tag=22276,
        name="CompDealerQuoteType",
        field_type="INT",
        description="Competing dealer's quote type.",
        valid_values={
            "0": "Indicative (Bloomberg provided)",
            "1": "Executable (counterparty quoted)",
        },
    ),
    22485: FixFieldDefinition(
        tag=22485,
        name="CompDealerQuoteSpotRate",
        field_type="PRICE",
        description=(
            "Dealer's spot rate factored into the all-in rate shown in "
            "CompDealerQuotePrice (10011)."
        ),
    ),
    22486: FixFieldDefinition(
        tag=22486,
        name="CompDealerQuoteTradeSide",
        field_type="INT",
        description=(
            "Which trade side the competing dealer's price applies to when "
            "the quote was two-sided."
        ),
        valid_values={
            "0": "Traded side (default)",
            "1": "Non-traded side",
        },
    ),
    22526: FixFieldDefinition(
        tag=22526,
        name="CompDealerRefID",
        field_type="STRING",
        description="ID reference of the competing dealer's quote or order.",
    ),
    22527: FixFieldDefinition(
        tag=22527,
        name="CompDealerRefIDSource",
        field_type="INT",
        description="What identifier is referenced in CompDealerRefID (22526).",
        valid_values={
            "1": "QuoteID (117)",
        },
    ),
    22565: FixFieldDefinition(
        tag=22565,
        name="CompDealerQuoteForwardPointsLeg2",
        field_type="PRICEOFFSET",
        description=("For FX swaps: dealer's far leg forward points, in decimal form."),
    ),
    # Observed inside CompDealerQuoteGrp entries on MAP execution reports but
    # not defined in the ORP 1.9.8 spec — kept as a group member so entry
    # detection stays intact. Rename once a newer Bloomberg spec names it.
    22545: FixFieldDefinition(
        tag=22545,
        name="CompDealerQuoteField22545",
        field_type="STRING",
        description=(
            "Undocumented CompDealerQuoteGrp member (not in the ORP 1.9.8 "
            "specification; observed on Bloomberg MAP execution reports)."
        ),
    ),
}


class BloombergDORHandler(VenueHandler):
    """Handler for Bloomberg DOR (Derivatives Order Routing) FIX messages."""

    @property
    def name(self) -> str:
        return "Bloomberg DOR"

    @property
    def sender_comp_ids(self) -> list[str]:
        return ["BLOOMBERG_DOR", "BBGDOR", "DOR", "FXOM", "ORP"]

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        """Return Bloomberg DOR custom tag definitions."""
        return list(_BLOOMBERG_CUSTOM_TAGS.values())

    @property
    def enum_extensions(self) -> dict[int, dict[str, str]]:
        """Bloomberg-specific enum codes that extend standard FIX fields."""
        return {
            # PartySubIDType: Bloomberg ORP/DOR private codes — 4025 marks a
            # PartySubID carrying an ISO 17442 Legal Entity Identifier (LEI);
            # 4046/4047 flag the party's liquidity role (Y/N PartySubID).
            803: {
                "4025": "Legal Entity Identifier",
                "4046": "Liquidity maker",
                "4047": "Liquidity taker",
            },
            # QuoteStatus: ORP/DOR codes above the standard FIX 4.4 range, sent
            # on QuoteStatusReport (35=AI) to report the outcome of a taker's
            # QuoteResponse (35=AJ) hit/lift. The standard codes DOR also uses
            # (0 Accepted, 4 Canceled all, 5 Rejected, 7 Expired "dealer goes
            # subject", 11 Pass "dealer rejects", 17 Canceled) come from FIX 4.4.
            297: {
                "100": "Response timed out",
                "101": "Trade ended",
                "104": "Begin spot",
                "105": "Due In Time lifted",
                "106": "Total Trade Time exceeded",
                "108": "Dealers added",
                "109": "Unpass",
                "110": "Trader changed",
                "111": "Transitioned to manual",
            },
            # QuoteRejectReason: ORP/DOR codes accompanying QuoteStatus(297)=5
            # (Rejected). 8 (Invalid price) and 99 (Other) come from FIX 4.4;
            # when 300=99 the plain-text reason is carried in RejectText(1328).
            300: {
                "110": "Best execution not supported",
                "111": "Dealer left the negotiation",
                "112": "Trade previously filled or ended",
                "113": "Another hit/lift is pending",
                "114": "Maker rejection",
                "115": "Negotiation system rejection",
                "116": "Trade record not found",
            },
        }

    def claims_message(self, message: FixMessage) -> bool:
        """Claim Bloomberg ORP/DOR messages by their protocol markers, even when
        only a generic Bloomberg CompID (e.g. 49=BLOOMBERG) matched — so they are
        not mis-detected as Bloomberg FXGO.

        Requires BOTH a Bloomberg CompID and a DOR/ORP protocol marker, so the
        claim can never steal another venue's FIXT.1.1 traffic. MAP gateway
        sessions are the exception: a MAP_BLP* CompID is Bloomberg-specific on
        its own, and MAP traffic is plain FIX 4.4 with none of the FIXT / 115 /
        128 markers.
        """
        comp_ids = {(message.get_value(tag) or "").upper() for tag in (49, 56, 115, 128)}
        # Bloomberg MAP gateway (FIX 4.4 flavor of the ORP/DOR dialect).
        if any(cid.startswith(_MAP_BLOOMBERG_PREFIX) for cid in comp_ids):
            return True
        if comp_ids.isdisjoint(_BLOOMBERG_COMP_IDS):
            return False
        # DOR/ORP routing markers on OnBehalfOfCompID (115) / DeliverToCompID (128).
        if (message.get_value(115) or "").upper() in _DOR_ROUTING_IDS:
            return True
        if (message.get_value(128) or "").upper() in _DOR_ROUTING_IDS:
            return True
        # DOR-only FIX 5.0 message types: QuoteStatusReport (AI), QuoteRequestReject (AG).
        if message.msg_type in ("AI", "AG"):
            return True
        # FIXT 1.1 session / FIX 5.0 application layer — Bloomberg FXGO is plain FIX 4.4.
        if message.begin_string == "FIXT.1.1":
            return True
        if message.get_value(1128):
            return True
        return False
