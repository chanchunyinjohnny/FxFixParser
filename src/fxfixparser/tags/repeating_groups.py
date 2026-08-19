"""FIX repeating group definitions.

This module defines the structure of repeating groups in FIX messages.
Each group is defined by a count tag (NUMINGROUP type) and the list of
tags that belong to each group entry.
"""

from dataclasses import dataclass, field


@dataclass
class RepeatingGroupDefinition:
    """Definition of a repeating group structure."""

    count_tag: int  # The NUMINGROUP tag that indicates how many entries follow
    name: str  # Human-readable name for the group
    member_tags: set[int]  # Tags that belong to each group entry
    # Members that come from a *nested* subgroup flattened into this one. The
    # entry-boundary rule ("a member tag seen twice starts a new entry") must
    # not apply to them: a nested subgroup legitimately repeats its own tags
    # inside a single parent entry (e.g. one MAPI party carries two or three
    # PartySubIDs, one MAPI TradeCaptureReport side carries two SettlDetails).
    # Only tags that identify a *parent* entry may open a new one.
    nested_member_tags: set[int] = field(default_factory=set)


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
            # Quote type of the entry (360T SUN mid / limit book entries)
            1070,  # MDQuoteType
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
        # A MAPI ExecutionReport party carries 2-3 PartySubIDs (TCID, trader,
        # and the FX Swap negotiation user), so 523/803 repeat within one party.
        nested_member_tags={523, 803},
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
            31344,  # TR_TradingCapacity (MAPI MiFID II)
            31345,  # TR_Npft (MAPI MiFID II)
            126,  # ExpireTime
            # Nested LimitAmts(1630) and SettlDetails(1158) subgroups, flattened
            # into the side. MAPI's TradeCaptureReport puts the bilateral credit
            # block and both parties' settlement instructions *inside* each side
            # (spec 5.4.16 / chapter 7.2.5); without these the walker terminates
            # the side at the first nested count tag and the whole tail of the
            # side — and, on a two-sided swap report, the entire second side —
            # leaks out as message-level fields.
            1630,  # NoLimitAmts
            1631,  # LimitAmtType
            1632,  # LastLimitAmt
            1633,  # LimitAmtRemaining
            1634,  # LimitAmtCurrency
            1158,  # NoSettlDetails
            1164,  # SettlObligSource
            781,  # NoSettlPartyIDs
            782,  # SettlPartyID
            783,  # SettlPartyIDSource
            784,  # SettlPartyRole
            801,  # NoSettlPartySubIDs
            785,  # SettlPartySubID
            786,  # SettlPartySubIDType
        },
        # Everything from the two nested subgroups repeats within a single side
        # (a MAPI side carries two SettlDetails instances), so none of it may
        # open a new side — only a repeated Side(54) does.
        nested_member_tags={
            1630,
            1631,
            1632,
            1633,
            1634,
            1158,
            1164,
            781,
            782,
            783,
            784,
            801,
            785,
            786,
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
            681,  # LegBidPx
            684,  # LegOfferPx
            685,  # LegOrderQty (FIX 5.0+, added via fx_tags)
            686,  # LegPriceType
            687,  # LegQty
            1788,  # LegID (FIX 5.0+; used by Bloomberg DOR swap legs)
            # FIX 5.0+ leg-level price/forward-point fields seen in
            # Bloomberg DOR swap RFQs, quotes, status and execution reports.
            607,  # LegProduct
            675,  # LegSettlCurrency
            1067,  # LegBidForwardPoints
            1068,  # LegOfferForwardPoints
            1073,  # LegLastForwardPoints (executed swap legs)
            2346,  # LegMidPx
            1074,  # LegCalculatedCcyLastQty (LSEG FX Matching swap legs)
            1418,  # LegLastQty (Bloomberg DOR executed leg amount)
            1893,  # LegExecID (per-leg execution ID)
            # Bloomberg DOR leg-scoped custom tags (defined in the venue
            # overlay); must be members so they don't terminate the walker.
            22010,  # LegTenor
            22041,  # LegDV01
            22263,  # LegCalculatedCurrency
            # 360T leg-level allocation (flattened nested NoLegAllocs) + leg mid.
            # 360T accepts only one allocation per leg, so 671/673 never repeat
            # within a leg and the flattening does not phantom-split entries.
            670,  # NoLegAllocs (nested leg-allocation count, flattened)
            671,  # LegAllocAccount
            673,  # LegAllocQty
            7652,  # LegMidPx (360T)
            # 360T SUN credit-check legs (PartyRiskLimitCheckRequest/Ack):
            # per-leg opposite amount and NDS fixing date.
            9622,  # LegOppositeOrderQty (360T SUN)
            7543,  # FixingDate (360T SUN, per credit-check leg)
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
    # Orders in a list. 360T SUN's NewOrderList (a "Strip" of linked FX Swap /
    # NDS limit orders) puts a complete order in each entry, so the members
    # cover the order economics plus the nested NoPartyIDs(453) and
    # NoOrderAttributes(2593) subgroups flattened into it. ClOrdID(11) opens
    # each entry.
    RepeatingGroupDefinition(
        count_tag=73,  # NoOrders
        name="Orders",
        member_tags={
            11,  # ClOrdID
            526,  # SecondaryClOrdID
            67,  # ListSeqNo
            583,  # ClOrdLinkID
            160,  # SettlInstMode
            1,  # Account
            15,  # Currency
            38,  # OrderQty
            40,  # OrdType
            44,  # Price
            54,  # Side
            55,  # Symbol
            59,  # TimeInForce
            64,  # SettlDate (near leg)
            110,  # MinQty
            126,  # ExpireTime
            192,  # OrderQty2 (far leg)
            193,  # SettlDate2 (far leg)
            1822,  # MinQtyMethod
            # Nested NoPartyIDs(453) and NoOrderAttributes(2593), flattened.
            453,  # NoPartyIDs
            447,  # PartyIDSource
            448,  # PartyID
            452,  # PartyRole
            2376,  # PartyRoleQualifier
            2593,  # NoOrderAttributes
            2594,  # OrderAttributeType
            2595,  # OrderAttributeValue
            # 360T SUN order tags (defined in the SUN venue overlay).
            7071,  # ProductType
            7075,  # FixingReference (NDS)
            7543,  # FixingDate (NDS near leg)
            7545,  # FixingDate2 (NDS far leg)
            9821,  # OppositeMatchingAllowed
            9822,  # UnevenSwapAllowed
        },
        # A single order carries several party entries and may carry several
        # order attributes, so those tags repeat inside one entry — only a
        # repeated parent tag (ClOrdID first among them) opens a new order.
        nested_member_tags={447, 448, 452, 2376, 2594, 2595},
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
        # On a MAPI TradeCaptureReport the report owner's block always carries
        # two RootPartySubIDs (TCID then trader login), so 1121/1122 repeat
        # within one party.
        nested_member_tags={1121, 1122},
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
        nested_member_tags={785, 786},
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
        # 1164 delimits each SettlDetails entry; everything below it comes from
        # the nested SettlParties(781)/SettlPartySubIDs(801) subgroups.
        nested_member_tags={781, 782, 783, 784, 801, 785, 786},
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
            # 360T SUN calendar entries: the far-leg value date, the NDS fixing
            # dates/reference and the EFP futures contract details.
            9612,  # UnderlyingMaturityDate2 (far-leg value date)
            9823,  # UnderlyingFixingDate (near leg)
            9824,  # UnderlyingFixingDate2 (far leg)
            9825,  # UnderlyingFixingReference
            2620,  # UnderlyingFutureID (EFP)
            2621,  # UnderlyingFutureIDSource (EFP)
            5242,  # UnderlyingLastTradingDate (EFP)
        },
    ),
    # Regulatory trade IDs (FIX 5.0 SP2; 360T / Bloomberg DOR ExecutionReport)
    RepeatingGroupDefinition(
        count_tag=1907,  # NoRegulatoryTradeIDs
        name="Regulatory Trade IDs",
        member_tags={
            1903,  # RegulatoryTradeID
            1905,  # RegulatoryTradeIDSource
            1904,  # RegulatoryTradeIDEvent
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
    # Competing dealer quotes (Bloomberg ORP/DOR & MAP Quote / ExecutionReport).
    # Tag names live in the Bloomberg DOR venue overlay.
    RepeatingGroupDefinition(
        count_tag=10009,  # NoCompDealerQuotes
        name="Competing Dealer Quotes",
        member_tags={
            10010,  # CompDealerID (entry delimiter)
            10011,  # CompDealerQuotePrice
            22161,  # CompDealerQuotePriceLeg2
            22162,  # CompDealerQuoteForwardPoints
            22163,  # CompDealerQuoteSwapPoints
            22276,  # CompDealerQuoteType
            22485,  # CompDealerQuoteSpotRate
            22486,  # CompDealerQuoteTradeSide
            22526,  # CompDealerRefID
            22527,  # CompDealerRefIDSource
            22565,  # CompDealerQuoteForwardPointsLeg2
            22545,  # undocumented MAP member (see Bloomberg DOR overlay)
        },
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
