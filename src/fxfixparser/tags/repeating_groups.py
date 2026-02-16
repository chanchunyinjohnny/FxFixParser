"""FIX repeating group definitions.

This module defines the structure of repeating groups in FIX messages.
Each group is defined by a count tag (NUMINGROUP type) and the list of
tags that belong to each group entry.
"""

from dataclasses import dataclass


@dataclass
class RepeatingGroupDefinition:
    """Definition of a repeating group structure."""

    count_tag: int  # The NUMINGROUP tag that indicates how many entries follow
    name: str  # Human-readable name for the group
    member_tags: set[int]  # Tags that belong to each group entry


# Standard FIX 4.4 repeating groups commonly used in FX
REPEATING_GROUPS: list[RepeatingGroupDefinition] = [
    # Market Data entries (MarketDataSnapshotFullRefresh, MarketDataIncrementalRefresh)
    RepeatingGroupDefinition(
        count_tag=268,  # NoMDEntries
        name="Market Data Entries",
        member_tags={
            269,  # MDEntryType
            270,  # MDEntryPx
            271,  # MDEntrySize
            272,  # MDEntryDate
            273,  # MDEntryTime
            274,  # TickDirection
            275,  # MDMkt
            276,  # QuoteCondition
            277,  # TradeCondition
            278,  # MDEntryID
            279,  # MDUpdateAction
            280,  # MDEntryRefID
            282,  # MDEntryOriginator
            283,  # LocationID
            284,  # DeskID
            286,  # OpenCloseSettlFlag
            290,  # MDEntryPositionNo
            291,  # FinancialStatus
            292,  # CorporateAction
            15,   # Currency
            64,   # SettlDate
            40,   # OrdType
            # Size/quantity fields within MD entries
            110,  # MinQty
            # Forward market data components
            1026,  # MDEntrySpotRate
            1027,  # MDEntryForwardPoints
            # Venue-specific custom tags commonly used in market data
            9122,  # VenueEntryTime
            9123,  # VenueEntryDate
            # Additional standard tags that may appear in entries
            37,   # OrderID
            198,  # SecondaryOrderID
            336,  # TradingSessionID
            625,  # TradingSessionSubID
            58,   # Text
        },
    ),
    # Market Data entry types request
    RepeatingGroupDefinition(
        count_tag=267,  # NoMDEntryTypes
        name="Market Data Entry Types",
        member_tags={
            269,  # MDEntryType
        },
    ),
    # Party IDs (used in many message types)
    RepeatingGroupDefinition(
        count_tag=453,  # NoPartyIDs
        name="Party IDs",
        member_tags={
            448,  # PartyID
            447,  # PartyIDSource
            452,  # PartyRole
            802,  # NoPartySubIDs (nested group)
        },
    ),
    # Related symbols (Quote Request, Market Data Request)
    RepeatingGroupDefinition(
        count_tag=146,  # NoRelatedSym
        name="Related Symbols",
        member_tags={
            55,   # Symbol
            65,   # SymbolSfx
            48,   # SecurityID
            22,   # SecurityIDSource
            167,  # SecurityType
            207,  # SecurityExchange
            106,  # Issuer
            107,  # SecurityDesc
            15,   # Currency
            64,   # SettlDate
            54,   # Side
            38,   # OrderQty
            63,   # SettlType
            193,  # SettlDate2
            192,  # OrderQty2
            126,  # ExpireTime
            # LFX custom tags for FX Swaps
            8004,  # SettlType2 (Far Leg Tenor)
        },
    ),
    # Legs (for multi-leg instruments like swaps)
    RepeatingGroupDefinition(
        count_tag=555,  # NoLegs
        name="Legs",
        member_tags={
            600,  # LegSymbol
            602,  # LegSecurityID
            603,  # LegSecurityIDSource
            604,  # NoLegSecurityAltID
            608,  # LegCFICode
            609,  # LegSecurityType
            610,  # LegMaturityMonthYear
            611,  # LegMaturityDate
            612,  # LegStrikePrice
            613,  # LegOptAttribute
            614,  # LegContractMultiplier
            615,  # LegCouponRate
            616,  # LegSecurityExchange
            617,  # LegIssuer
            618,  # LegSecurityDesc
            619,  # LegRatioQty
            620,  # LegSide
            621,  # EncodedLegSecurityDescLen
            622,  # LegPool
            623,  # LegDatedDate
            624,  # LegContractSettlMonth
            556,  # LegCurrency
            564,  # LegPositionEffect
            565,  # LegCoveredOrUncovered
            566,  # LegPrice
            587,  # LegSettlType
            588,  # LegSettlDate
            637,  # LegLastPx
            654,  # LegRefID
            682,  # LegIOIQty
            683,  # NoLegStipulations
            684,  # LegOfferPx
            685,  # LegOrderQty (FIX 5.0+, added via fx_tags)
            686,  # LegPriceType
            687,  # LegQty
        },
    ),
    # Allocations
    RepeatingGroupDefinition(
        count_tag=78,  # NoAllocs
        name="Allocations",
        member_tags={
            79,   # AllocAccount
            661,  # AllocAcctIDSource
            573,  # MatchStatus
            366,  # AllocPrice
            80,   # AllocQty
            467,  # IndividualAllocID
            81,   # ProcessCode
            736,  # AllocSettlCurrency
            737,  # AllocSettlCurrAmt
            161,  # AllocText
        },
    ),
    # Orders in a list
    RepeatingGroupDefinition(
        count_tag=73,  # NoOrders
        name="Orders",
        member_tags={
            11,   # ClOrdID
            526,  # SecondaryClOrdID
            67,   # ListSeqNo
            583,  # ClOrdLinkID
            160,  # SettlInstMode
        },
    ),
    # Fills/Executions
    RepeatingGroupDefinition(
        count_tag=1362,  # NoFills
        name="Fills",
        member_tags={
            1363,  # FillExecID
            1364,  # FillPx
            1365,  # FillQty
            1443,  # FillLiquidityInd
        },
    ),
    # Security trading rules
    RepeatingGroupDefinition(
        count_tag=1141,  # NoTradingSessionRules
        name="Trading Session Rules",
        member_tags={
            336,  # TradingSessionID
            625,  # TradingSessionSubID
        },
    ),
]


def get_group_definition(count_tag: int) -> RepeatingGroupDefinition | None:
    """Get the repeating group definition for a given count tag.

    Args:
        count_tag: The NUMINGROUP tag number.

    Returns:
        The group definition if found, None otherwise.
    """
    for group in REPEATING_GROUPS:
        if group.count_tag == count_tag:
            return group
    return None


def is_count_tag(tag: int) -> bool:
    """Check if a tag is a repeating group count tag."""
    return any(group.count_tag == tag for group in REPEATING_GROUPS)