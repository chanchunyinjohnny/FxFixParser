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
            15,  # Currency
            64,  # SettlDate
            40,  # OrdType
            # Size/quantity fields within MD entries
            110,  # MinQty
            # Forward market data components
            1026,  # MDEntrySpotRate
            1027,  # MDEntryForwardPoints
            # Venue-specific custom tags commonly used in market data
            9122,  # VenueEntryTime
            9123,  # VenueEntryDate
            # Additional standard tags that may appear in entries
            37,  # OrderID
            198,  # SecondaryOrderID
            336,  # TradingSessionID
            625,  # TradingSessionSubID
            58,  # Text
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
            802,  # NoPartySubIDs (nested group count)
            # Nested PartySubIDs (802) child tags. Treated as flat members
            # of the parent so the walker doesn't terminate the party entry
            # on them — loses nested structure but keeps the count correct.
            523,  # PartySubID
            803,  # PartySubIDType
            # 360T TI carries the MiFID2 party role qualifier inside party
            # entries (e.g. Investment Decision Maker / Executing Trader).
            2376,  # PartyRoleQualifier
        },
    ),
    # Sides (Trade Capture Report side-level details)
    RepeatingGroupDefinition(
        count_tag=552,  # NoSides
        name="Sides",
        member_tags={
            54,  # Side
            1,  # Account
            11,  # ClOrdID
            15,  # Currency
            31,  # LastPx
            32,  # LastQty
            37,  # OrderID
            38,  # OrderQty
            44,  # Price
            58,  # Text
            120,  # SettlCurrency
            1005,  # SideTradeReportID
            1009,  # SideLastQty
            1427,  # SideExecID
            1506,  # SideTradeID
            1507,  # SideOrigTradeID
            1597,  # SideClearingTradePrice
            # LSEG FX Matching side-level tags (TradeCaptureReport NoSides entry).
            # MAPI's proprietary MiFID tags stay venue-scoped in the dictionary
            # overlay, but must still be group members so structured parsing
            # does not terminate NoSides early.
            1154,  # SideCurrency
            1057,  # AggressorIndicator
            1097,  # LastLimitAmt (MAPI FXSPOT credit drawn; std PegSecurityID)
            1149,  # LimitRemainingAmt (MAPI FXSPOT credit remaining; std HighLimitPrice)
            31344,  # TR_TradingCapacity (MAPI MiFID II)
            31345,  # TR_Npft (MAPI MiFID II)
            126,  # ExpireTime
        },
    ),
    # Related symbols (Quote Request, Market Data Request)
    RepeatingGroupDefinition(
        count_tag=146,  # NoRelatedSym
        name="Related Symbols",
        member_tags={
            55,  # Symbol
            65,  # SymbolSfx
            48,  # SecurityID
            22,  # SecurityIDSource
            167,  # SecurityType
            207,  # SecurityExchange
            106,  # Issuer
            107,  # SecurityDesc
            15,  # Currency
            64,  # SettlDate
            54,  # Side
            38,  # OrderQty
            63,  # SettlType
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
            624,  # LegSide (FIX 5.0+ reuses this tag — was LegContractSettlMonth in 4.2)
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
            1788,  # LegID (FIX 5.0+; used by Bloomberg DOR swap legs)
            # FIX 5.0+ leg-level price/forward-point fields seen in
            # Bloomberg DOR swap RFQs, quotes, and status reports.
            607,  # LegProduct
            1067,  # LegBidForwardPoints
            1068,  # LegOfferForwardPoints
            2346,  # LegMidPx
            1074,  # LegCalculatedCcyLastQty (standard)
            1418,  # LegCalculatedCcyLastQty (LSEG variant; standard LegLastQty)
            # 360T leg-level allocation (flattened nested NoLegAllocs) + leg mid.
            # 360T accepts only one allocation per leg, so 671/673 never repeat
            # within a leg and the flattening does not phantom-split entries.
            670,  # NoLegAllocs (nested leg-allocation count, flattened)
            671,  # LegAllocAccount
            673,  # LegAllocQty
            7652,  # LegMidPx (360T)
        },
    ),
    # Allocations
    RepeatingGroupDefinition(
        count_tag=78,  # NoAllocs
        name="Allocations",
        member_tags={
            79,  # AllocAccount
            661,  # AllocAcctIDSource
            573,  # MatchStatus
            366,  # AllocPrice
            80,  # AllocQty
            467,  # IndividualAllocID
            81,  # ProcessCode
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
            11,  # ClOrdID
            526,  # SecondaryClOrdID
            67,  # ListSeqNo
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
    # Stipulations (LSEG forward-swap negotiation; Quote / TradeCaptureReport)
    RepeatingGroupDefinition(
        count_tag=232,  # NoStipulations
        name="Stipulations",
        member_tags={
            233,  # StipulationType
            234,  # StipulationValue
        },
    ),
    # Strategy parameters (Iceberg orders)
    RepeatingGroupDefinition(
        count_tag=957,  # NoStrategyParameters
        name="Strategy Parameters",
        member_tags={
            958,  # StrategyParameterName
            959,  # StrategyParameterType
            960,  # StrategyParameterValue
        },
    ),
    # Root Parties (LSEG TradeCaptureReport carries party identity here, not 453)
    RepeatingGroupDefinition(
        count_tag=1116,  # NoRootPartyIDs
        name="Root Parties",
        member_tags={
            1117,  # RootPartyID
            1118,  # RootPartyIDSource
            1119,  # RootPartyRole
            # Nested RootPartySubIDs (1120) children, flattened (as 453/802).
            1120,  # NoRootPartySubIDs
            1121,  # RootPartySubID
            1122,  # RootPartySubIDType
        },
    ),
    # Settlement Parties (CLS / payment instructions)
    RepeatingGroupDefinition(
        count_tag=781,  # NoSettlPartyIDs
        name="Settlement Parties",
        member_tags={
            782,  # SettlPartyID
            783,  # SettlPartyIDSource
            784,  # SettlPartyRole
            # Nested SettlPartySubIDs (801) children, flattened.
            801,  # NoSettlPartySubIDs
            785,  # SettlPartySubID
            786,  # SettlPartySubIDType
        },
    ),
    # Settlement Details (LSEG TradeCaptureReport; nests SettlParties)
    RepeatingGroupDefinition(
        count_tag=1158,  # NoSettlDetails
        name="Settlement Details",
        member_tags={
            1164,  # SettlObligSource
            # Nested SettlParties (781) flattened into the parent.
            781,  # NoSettlPartyIDs
            782,  # SettlPartyID
            783,  # SettlPartyIDSource
            784,  # SettlPartyRole
            801,  # NoSettlPartySubIDs
            785,  # SettlPartySubID
            786,  # SettlPartySubIDType
        },
    ),
    # Limit Amounts (LSEG FXSPOT credit limits)
    RepeatingGroupDefinition(
        count_tag=1630,  # NoLimitAmts
        name="Limit Amounts",
        member_tags={
            1631,  # LimitAmtType
            1632,  # LastLimitAmt
            1633,  # LimitAmtRemaining
            1634,  # LimitAmtCurrency
        },
    ),
    # Order Attributes (MiFID II liquidity-provision flag)
    RepeatingGroupDefinition(
        count_tag=2593,  # NoOrderAttributes
        name="Order Attributes",
        member_tags={
            2594,  # OrderAttributeType
            2595,  # OrderAttributeValue
        },
    ),
    # Hops (FIXT 1.1 message routing)
    RepeatingGroupDefinition(
        count_tag=627,  # NoHops
        name="Hops",
        member_tags={
            628,  # HopCompID
            629,  # HopSendingTime
            630,  # HopRefID
        },
    ),
    # 360T custom fields (QuoteRequest / ExecutionReport)
    RepeatingGroupDefinition(
        count_tag=7546,  # NoCustomFields
        name="Custom Fields",
        member_tags={
            7547,  # CustomFieldName
            7548,  # CustomFieldValue
        },
    ),
    # Underlyings (360T SecurityDefinition tenor / value-date calendar)
    RepeatingGroupDefinition(
        count_tag=711,  # NoUnderlyings
        name="Underlyings",
        member_tags={
            311,  # UnderlyingSymbol
            305,  # UnderlyingSecurityIDSource
            309,  # UnderlyingSecurityID (tenor short name)
            312,  # UnderlyingSymbolSfx
            307,  # UnderlyingSecurityDesc (tenor long name)
            542,  # UnderlyingMaturityDate (value date)
        },
    ),
    # Regulatory trade IDs (FIX 5.0 SP2; 360T ExecutionReport)
    RepeatingGroupDefinition(
        count_tag=1907,  # NoRegulatoryTradeIDs
        name="Regulatory Trade IDs",
        member_tags={
            1903,  # RegulatoryTradeID
            1905,  # RegulatoryTradeIDSource
            1906,  # RegulatoryTradeIDType
            2411,  # RegulatoryLegRefID
        },
    ),
    # Security alternate IDs (360T TI per-leg ISINs / contract codes)
    RepeatingGroupDefinition(
        count_tag=454,  # NoSecurityAltID
        name="Security Alt IDs",
        member_tags={
            455,  # SecurityAltID
            456,  # SecurityAltIDSource
        },
    ),
    # Regulatory publications — waivers / deferrals (MiFID2; 360T TI)
    RepeatingGroupDefinition(
        count_tag=2668,  # NoTrdRegPublications
        name="Regulatory Publications",
        member_tags={
            2669,  # TrdRegPublicationType
            2670,  # TrdRegPublicationReason
        },
    ),
    # Competing dealer quotes (360T TI ExecutionReport). 9519 and 9521 are gaps
    # in 360T's numbering — excluded so they are never treated as members.
    RepeatingGroupDefinition(
        count_tag=9516,  # NoCompetingQuotes
        name="Competing Quotes",
        member_tags=set(range(9517, 9544)) - {9519, 9521},  # 9517–9543
    ),
    # Payment schedule (360T TI commodity Asian swaps / energy Asian options)
    RepeatingGroupDefinition(
        count_tag=7560,  # NoPaymentSchedule
        name="Payment Schedule",
        member_tags={
            7561,  # PaymentScheduleYearMonth
            7562,  # PaymentScheduleAmount
        },
    ),
    # Negotiation external IDs (360T TI)
    RepeatingGroupDefinition(
        count_tag=9580,  # NoNegotiationExternalIds
        name="Negotiation External IDs",
        member_tags={
            9581,  # NegotiationExternalId
        },
    ),
    # Trade-intention product-id mappings (360T TI)
    RepeatingGroupDefinition(
        count_tag=9590,  # NoTIProductIds
        name="TI Product IDs",
        member_tags={
            9591,  # TIProductId
            9592,  # TIExternalId
        },
    ),
    # Reference prices (360T TI EMS workflow snapshots)
    RepeatingGroupDefinition(
        count_tag=9780,  # NoRefprices
        name="Reference Prices",
        member_tags=set(range(9781, 9793)),  # 9781–9792
    ),
    # Reference IDs (360T TI)
    RepeatingGroupDefinition(
        count_tag=9800,  # NoReferenceIDs
        name="Reference IDs",
        member_tags={
            9801,  # ReferenceIDType
            9802,  # ReferenceIDValue
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
