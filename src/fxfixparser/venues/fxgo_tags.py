"""Bloomberg FXGO custom tag definitions.

Field definitions for the three plain-FIX 4.4 Bloomberg FXGO interfaces:

- **FIXBOOK for Liquidity Providers** (v5.0.4): streaming/RFS quoting,
  market data, orders and executions between Bloomberg and price makers.
- **FXGO Algo (FXOM)** (FIX 4.4 Rev 1.5): algo order routing to makers.
- **FXGO STP** (FIX 4.4 Rev 1.0): post-trade drop copy and allocation
  notification for all FX products, including FX options.

All three dialects share one Bloomberg tag space with the ORP/DOR protocol;
the tags Bloomberg DOR also uses live in
``fxfixparser.venues.bloomberg_dor.BLOOMBERG_CUSTOM_TAGS`` and are merged by
the FXGO handler. Definitions below are FXGO-specific (or carry FXGO-specific
meanings). Names, types, descriptions and enumerated values are taken from
the Bloomberg specification tables — never invented.
"""

from fxfixparser.core.field import FixFieldDefinition


def _f(
    tag: int,
    name: str,
    field_type: str,
    description: str,
    valid_values: dict[str, str] | None = None,
) -> FixFieldDefinition:
    return FixFieldDefinition(tag, name, field_type, description, valid_values or {})


_YES_NO_12 = {"1": "Yes", "2": "No"}
_CASH_PHYSICAL = {"C": "Cash settlement required", "P": "Physical settlement required"}
_HEDGE_ID_SOURCE = {
    "4": "ISIN",
    "6": "ISO Currency Code",
    "A": "Bloomberg Identifier (BBID; STW options only)",
}
_HEDGE_TRADE_TYPE = {"1": "Spot hedge", "2": "Forward hedge", "3": "Custom"}
_BARRIER_DIRECTION = {
    "0": "Up and In",
    "1": "Down and In",
    "2": "Up and Out",
    "3": "Down and Out",
}
_COMPLEX_EVENT_TYPES = {
    "3": "Knock-in up",
    "4": "Knock-in down",
    "5": "Knock-out up",
    "6": "Knock-out down",
    "10": "One-touch",
    "11": "No-touch",
    "12": "Double one-touch",
    "13": "Double no-touch",
    "100": "Accrual range",
    "101": "Knock-in (TARF KI)",
}
_EVENT_PRICE_TIME = {"1": "Expiration", "2": "Immediate (at any time, e.g. hit)", "100": "Exercise"}
_EVENT_CONDITION = {"1": "And (digital ranges)", "2": "Or (multiple barriers)"}
_EXERCISE_STYLES = {"0": "European", "1": "American", "2": "Bermuda", "99": "Other"}
_ALLOC_REG_ID_TYPES = {
    "0": "Current (default if not specified)",
    "1": "Previous (cleared trade / novation)",
    "2": "Block (when reporting an allocated subtrade)",
    "3": "Related (when reporting a mixed swap)",
    "5": "Trading venue transaction identifier (MiFID II TVTIC)",
}
_EXERCISE_FREQ_UNITS = {"D": "Day", "Wk": "Week", "Mo": "Month", "Yr": "Year"}
_COUPON_DAY_COUNTS = {
    "6": "Act/360",
    "7": "Act/365 (FIXED)",
    "8": "Act/Act (AFB)",
    "12": "BUS/252",
    "100": "Act/30",
    "101": "Act/30 Compounded",
    "102": "Act/360 Compounded",
    "103": "Act/365 Compounded",
    "104": "Act/Act Compounded",
    "105": "BUS/252 Compounded",
}
_MARKET_SEGMENT_IDS = {
    "XOFF": "Off Facility (default)",
    "BSEF": "Bloomberg Swap Execution Facility",
    "BMTF": "Bloomberg Multilateral Trading Facility",
    "BTFE": "Bloomberg Trading Facility Europe",
    "BTBS": "Bloomberg Tradebook Singapore",
    "ANTA": "PT Antara Elektronik Transaksi Pratama",
}

FXGO_CUSTOM_TAGS: dict[int, FixFieldDefinition] = {
    # ------------------------------------------------------------------
    # FIXBOOK — streaming / RFS quoting between Bloomberg and LPs
    # ------------------------------------------------------------------
    5082: _f(
        5082,
        "QuoteType",
        "INT",
        "Whether the quote (request) is Manual or Executable All-in.",
        {
            "2": "Manual pricing (RFS)",
            "4": "Executable all-in pricing (static volume band streaming)",
        },
    ),
    6065: _f(
        6065,
        "StreamingQuoteDuration",
        "INT",
        "Number of seconds for which to receive price ticks.",
        {"0": "Receive quotes until logged out"},
    ),
    6050: _f(
        6050,
        "BidPx2",
        "PRICE",
        "All-in bid rate for the far leg of a forward-forward swap on a "
        "Manual (RFS) quote (QuoteType(5082)=2).",
    ),
    6051: _f(
        6051,
        "OfferPx2",
        "PRICE",
        "All-in offer rate for the far leg of a forward-forward swap on a "
        "Manual (RFS) quote (QuoteType(5082)=2).",
    ),
    6160: _f(6160, "LastPx2", "PRICE", "All-in rate of the far leg of an FX swap."),
    5191: _f(
        5191,
        "LegLastFowardPoints",  # [sic] — Bloomberg's spelling in the FIXBOOK spec
        "PRICEOFFSET",
        "Far leg forward points of a swap, in unscaled decimal convention "
        "(e.g. 8 points on EUR/USD is sent as 0.0008).",
    ),
    1028: _f(
        1028,
        "MDEntryForwardPoints2",
        "PRICEOFFSET",
        "FX swaps only: far leg forward points, in decimal form "
        "(61.99 points is sent as 0.006199).",
    ),
    9518: _f(
        9518,
        "MidRateNear",
        "PRICE",
        "Mid market rate (all-in) for a forward/NDF or the near leg of an FX "
        "swap. Pre-trade market mid provided by liquidity providers for the "
        "Dodd-Frank pre-trade market mid requirement (SEF).",
    ),
    9520: _f(
        9520,
        "MidRateFar",
        "PRICE",
        "Mid market rate (all-in) for the far leg of an FX swap. Pre-trade "
        "market mid provided by liquidity providers for the Dodd-Frank "
        "pre-trade market mid requirement (SEF).",
    ),
    9115: _f(
        9115,
        "MidSpotRate",
        "PRICE",
        "Mid market spot rate. Pre-trade market mid provided by liquidity "
        "providers for the Dodd-Frank pre-trade market mid requirement (SEF).",
    ),
    6216: _f(
        6216,
        "Tenor2",
        "TENOR",
        "Tenor code of the far leg of an FX swap (FIXBOOK: TenorValue2; "
        "mandatory for 2-legged deals). For BRL split settlement requests "
        "and split-settlement STP trades: the settlement tenor of CCY2. "
        "Same tenor-code domain as Tenor (6215).",
    ),
    5974: _f(5974, "FixingSource", "STRING", "Fixing source for an NDF."),
    6203: _f(
        6203,
        "FixingDate",
        "LOCALMKTDATE",
        "Fixing date for an NDF, in YYYYMMDD format. On FX Options / FX Algo "
        "STP drop copy: the hedge fixing date from CNFO.",
    ),
    5947: _f(
        5947,
        "LegFixingSource",
        "STRING",
        "For NDF legs: the fixing source of the leg.",
    ),
    9119: _f(
        9119,
        "FixingDate2",
        "LOCALMKTDATE",
        "Fixing date of the far leg; required for 2-legged non-deliverable " "swap (NDS) deals.",
    ),
    9120: _f(
        9120,
        "SettlCurrency2",
        "CURRENCY",
        "Settlement currency of the far leg; required for 2-legged "
        "non-deliverable swap (NDS) deals.",
    ),
    1445: _f(
        1445,
        "NoRateSources",
        "NUMINGROUP",
        "Number of rate sources in the repeating group (NDF fixing-rate "
        "sources; also required on FX Options drop copy when "
        "AutoExpiryFlag(22934)=Y).",
    ),
    1446: _f(
        1446,
        "RateSource",
        "INT",
        "Source of the (fixing) rate information. For FX: the reference "
        "source for the FX spot rate.",
        {
            "0": "Bloomberg (BFIX)",
            "1": "Reuters (WMR)",
            "99": "Other",
            "100": "EMTA (Settlement Rate Option per the EMTA NDF template terms)",
            "101": "LBMA (London Bullion Market Association)",
        },
    ),
    1447: _f(
        1447,
        "RateSourceType",
        "INT",
        "Whether the rate source specified is a primary or secondary source.",
        {"0": "Primary", "1": "Secondary"},
    ),
    1448: _f(
        1448,
        "ReferencePage",
        "STRING",
        "Reference 'page' from the rate source; for FX, the reference page "
        "for the FX spot rate.",
    ),
    6702: _f(
        6702,
        "InCompetition",
        "BOOLEAN",
        "Indicates if the request is in competition.",
        {"Y": "Yes, request is in competition", "N": "No, request is not in competition"},
    ),
    6521: _f(
        6521,
        "CounterpartyReference",
        "STRING",
        "Free-text identification of a counterparty who is not a member of the exchange.",
    ),
    5177: _f(5177, "Source", "STRING", "Identifies the system source, e.g. 'Tradebook'."),
    5178: _f(
        5178,
        "Dealer",
        "STRING",
        "The bank/dealer that a trade was done with.",
    ),
    9170: _f(
        9170,
        "CLExecID",
        "STRING",
        "Client execution ID — the execution-report ID of a previous FX "
        "trade report sent to Bloomberg by another system.",
    ),
    1166: _f(
        1166,
        "QuoteMsgID",
        "STRING",
        "Optional message identifier supplied on a quote cancel.",
    ),
    6812: _f(
        6812,
        "DepoActionType",
        "STRING",
        "FX deposits: whether this is a new trade or an old trade being "
        "renewed (rolled) with the same dealer under new settlement and "
        "termination dates. (STP spec name: ActionType.)",
        {"N": "New (default)", "R": "Rollover"},
    ),
    6813: _f(
        6813,
        "DepoDayCount",
        "CHAR",
        "FX deposit day count fraction.",
        {
            "0": "ACT/360",
            "1": "ACT/360 (Comp)",
            "3": "30/360",
            "5": "ACT/365",
            "6": "ACT/365 (Comp)",
            "7": "ACT/30",
            "8": "ACT/30 (Comp)",
            "a": "ACT/ACT",
            "B": "BIZ/252",
            "C": "BIZ/252 (Comp)",
        },
    ),
    1036: _f(
        1036,
        "ExecAckStatus",
        "CHAR",
        "Status of the execution acknowledgement (35=BN).",
        {
            "1": "Accepted (trade details as reported are confirmed)",
            "2": "Don't know / Rejected",
        },
    ),
    # SEF / regulatory reporting (FIXBOOK)
    21807: _f(
        21807,
        "LiquidityTakerIsUSPerson",
        "INT",
        "Whether the liquidity taker is a US person (SEF requirement).",
        _YES_NO_12,
    ),
    21828: _f(
        21828,
        "LiquidityMakerUSPerson",
        "INT",
        "Whether the liquidity maker is a US person (SEF requirement).",
        _YES_NO_12,
    ),
    21833: _f(
        21833,
        "SwapReportingAgency",
        "STRING",
        "Reporting agency (SDR) where the trade will be reported, e.g. DTCC " "(SEF requirement).",
    ),
    21834: _f(21834, "BloombergSEFID", "STRING", "Bloomberg SEF ID (SEF requirement)."),
    21835: _f(
        21835,
        "ReportingParty",
        "INT",
        "Which party reports the trade (SEF requirement).",
        {"1": "Liquidity Maker", "2": "Liquidity Taker"},
    ),
    1938: _f(
        1938,
        "AssetClass",
        "INT",
        "Broad asset category for assessing risk exposure.",
        {"2": "Currency", "5": "Commodity (precious metals)"},
    ),
    2489: _f(
        2489,
        "PackageID",
        "STRING",
        "Identifier assigned to a collection of two or more derivative "
        "trades analyzed as a single atomic unit for risk assessment "
        "(MiFID II; required for BMTF/BTFE, optional for XOFF).",
    ),
    2891: _f(
        2891,
        "UPICode",
        "STRING",
        "Unique Product Identifier (UPI) using ISO 4914. For FXSWAP/FXNDS "
        "the per-leg UPIs ride in NearFxUPICode (22896) / FarFxUPICode (22897).",
    ),
    2893: _f(
        2893,
        "LegUPICode",
        "STRING",
        "Unique Product Identifier (UPI, ISO 4914) of the leg security.",
    ),
    22432: _f(
        22432,
        "SettlQualifier",
        "INT",
        "Qualifier for the settlement type and date fields (BRL split " "settlement requests).",
        {"0": "Split settlement (see SettlDate(64), SettlDate2(193), Tenor(6215), Tenor2(6216))"},
    ),
    22444: _f(
        22444,
        "NearFxISIN",
        "STRING",
        "ISIN of the near leg of an FXSWAP/FXNDS (BMTF/BTFE, when available "
        "at order submission).",
    ),
    22445: _f(
        22445,
        "FarFxISIN",
        "STRING",
        "ISIN of the far leg of an FXSWAP/FXNDS (BMTF/BTFE, when available "
        "at order submission).",
    ),
    22896: _f(
        22896,
        "NearFxUPICode",
        "STRING",
        "UPI (ISO 4914) of the near leg of an FXSWAP or FXNDS.",
    ),
    22897: _f(
        22897,
        "FarFxUPICode",
        "STRING",
        "UPI (ISO 4914) of the far leg of an FXSWAP or FXNDS.",
    ),
    # FIXBOOK batch RFQ workflow
    9112: _f(
        9112,
        "SymbolCcyRefID",
        "STRING",
        "Batch RFQ: identifier for an individual symbol/currency combination "
        "within the quote request; echoed back in the MassQuote (35=i). "
        "On FX Options STP drop copy Bloomberg reuses this tag as HedgeDate "
        "(the hedge date).",
    ),
    9114: _f(
        9114,
        "MakerListID",
        "STRING",
        "Daily unique identifier for a batch order, provided by the market maker.",
    ),
    20003: _f(
        20003,
        "LegRegulatoryTradeIDSource",
        "STRING",
        "Identifies the reporting entity that originated the leg regulatory "
        "trade ID (venue UTI prefix; an LEI of 20 alphanumeric characters).",
    ),
    20004: _f(
        20004,
        "LegRegulatoryTradeID",
        "STRING",
        "Leg-level regulatory trade identifier (USI / UTI) required by "
        "government regulators for regulatory reporting.",
    ),
    22410: _f(
        22410,
        "LegISINProduct",
        "STRING",
        "Product qualifier for the leg ISIN.",
        {"NDF": "Non-deliverable forward", "Forward": "Deliverable forward"},
    ),
    22412: _f(
        22412,
        "LegTradePublishIndicator",
        "INT",
        "Whether the leg trade should be reported via a market reporting "
        "service; governs all reporting services of the recipient.",
        {"0": "Not published", "1": "Publish trade", "2": "Deferred publication"},
    ),
    22413: _f(
        22413,
        "LegMarketSegmentID",
        "STRING",
        "Bloomberg market segment / execution facility identifier of the leg.",
        _MARKET_SEGMENT_IDS,
    ),
    22416: _f(
        22416,
        "NoLegTrdRegPublications",
        "NUMINGROUP",
        "Number of leg trade-publication entries (MiFID II pre-/post-trade "
        "transparency waivers and deferrals).",
    ),
    22417: _f(
        22417,
        "LegTrdType",
        "INT",
        "Securities Financing Transaction indicator for the leg; if present "
        "then securities financing is TRUE.",
        {"47": "Financing transaction"},
    ),
    22418: _f(
        22418,
        "LegLastCapacity",
        "CHAR",
        "Maker trading capacity for the leg (BMTF/BTFE).",
        {"4": "Principal (DEAL)"},
    ),
    22422: _f(
        22422,
        "LegTrdRegPublicationType",
        "INT",
        "MiFID II: indicates reduction of pre- or post-trade transparency " "for the leg.",
        {"0": "Pre-trade transparency waiver"},
    ),
    22423: _f(
        22423,
        "LegTrdRegPublicationReason",
        "INT",
        "MiFID II: reason qualifying LegTrdRegPublicationType (22422).",
        {
            "6": 'Deferral due to "Large in Scale"',
            "7": 'Deferral due to "Illiquid Instrument"',
            "8": 'Deferral due to "Size Specific"',
        },
    ),
    22424: _f(
        22424,
        "LegPackageID",
        "STRING",
        "Identifier assigned to a collection of two or more derivative "
        "trades analyzed as a single atomic unit for risk assessment, at "
        "the leg level.",
    ),
    22436: _f(
        22436,
        "LegTrdRegTimestamp",
        "UTCTIMESTAMP",
        "Leg execution regulatory timestamp (BMTF/BTFE): time the "
        "transaction was entered, in UTC.",
    ),
    22905: _f(
        22905,
        "LegRTN",
        "STRING",
        "Report tracking number (RTN) of the leg (EMIR Refit).",
    ),
    1367: _f(
        1367,
        "LegAllocSettlCurrency",
        "CURRENCY",
        "Settlement currency of the leg allocation; same as Currency (15).",
    ),
    1908: _f(
        1908,
        "NoAllocRegulatoryTradeIDs",
        "NUMINGROUP",
        "Number of allocation-level regulatory trade ID entries.",
    ),
    1909: _f(
        1909,
        "AllocRegulatoryTradeID",
        "STRING",
        "Regulatory trade identifier (USI / UTI) specific to this " "allocation account.",
    ),
    1910: _f(
        1910,
        "AllocRegulatoryTradeIDSource",
        "STRING",
        "Identifies the reporting entity that originated the value in "
        "AllocRegulatoryTradeID (1909) — venue UTI prefix; an LEI of 20 "
        "alphanumeric characters.",
    ),
    1911: _f(
        1911,
        "AllocRegulatoryTradeIDEvent",
        "INT",
        "Event causing origination of the identifier in " "AllocRegulatoryTradeID (1909).",
        {
            "0": "Initial block trade",
            "1": "Allocation (block trade will not be further allocated)",
        },
    ),
    1912: _f(
        1912,
        "AllocRegulatoryTradeIDType",
        "INT",
        "Type of trade identifier provided in AllocRegulatoryTradeID (1909) "
        "within the hierarchy of trade events.",
        _ALLOC_REG_ID_TYPES,
    ),
    22425: _f(
        22425,
        "LegAllocRegulatoryTradeID",
        "STRING",
        "Leg-level regulatory trade identifier (USI / UTI) specific to this " "allocation account.",
    ),
    22426: _f(
        22426,
        "LegAllocRegulatoryTradeIDSource",
        "STRING",
        "Identifies the reporting entity that originated the value in "
        "LegAllocRegulatoryTradeID (22425) — venue UTI prefix; an LEI of 20 "
        "alphanumeric characters.",
    ),
    22887: _f(
        22887,
        "NoLegAllocRegulatoryTradeIDs",
        "NUMINGROUP",
        "Number of leg allocation-level regulatory trade ID entries.",
    ),
    22888: _f(
        22888,
        "LegAllocRegulatoryTradeIDEvent",
        "INT",
        "Event causing origination of the identifier in " "LegAllocRegulatoryTradeID (22425).",
        {"1": "Allocation (block trade will not be further allocated)"},
    ),
    22889: _f(
        22889,
        "LegAllocRegulatoryTradeIDType",
        "INT",
        "Type of trade identifier provided in LegAllocRegulatoryTradeID "
        "(22425) within the hierarchy of trade events.",
        _ALLOC_REG_ID_TYPES,
    ),
    # ------------------------------------------------------------------
    # FXGO Algo (FXOM) — algo order routing
    # ------------------------------------------------------------------
    957: _f(957, "NoStrategyParameters", "NUMINGROUP", "Number of strategy parameters."),
    2431: _f(
        2431,
        "ExecTypeReason",
        "INT",
        "The initiating event when an ExecutionReport (35=8) is sent.",
        {
            "8": "Suspended order replaced upon request",
            "13": "Suspended order activated",
            "14": "Active order suspended",
        },
    ),
    22213: _f(
        22213,
        "AlgoStrategyName",
        "STRING",
        "Identifies the type of the order (algo strategy or resting). "
        "Upper-case strategy name matching the UI name with spaces and "
        "special characters removed (e.g. 'TWAP MAJOR' is sent as "
        "'TWAPMAJOR').",
    ),
    10006: _f(
        10006,
        "DayNetAvgSpot",
        "FLOAT",
        "Daily average rate at which the currency pair in Symbol (55) is "
        "filled, including commission. Sent when ExecType(150)=3 (Done for "
        "day) for multi-day orders.",
    ),
    10119: _f(
        10119,
        "DayNetContraCumQty",
        "AMT",
        "Daily cumulative quantity for the counter currency. Sent when "
        "ExecType(150)=3 (Done for day) for multi-day orders.",
    ),
    11026: _f(
        11026,
        "DayBaseAvgSpot",
        "FLOAT",
        "Daily average price during the life cycle of the order, excluding "
        "fees. Sent when ExecType(150)=3 (Done for day) for multi-day orders.",
    ),
    11027: _f(
        11027,
        "DayAvgPoints",
        "PRICEOFFSET",
        "Average of the forward points received in LastForwardPoints (195) "
        "during the life cycle of an order (FX forwards, multi-day orders).",
    ),
    22828: _f(22828, "LastAllInPx", "PRICE", "All-in price of the last execution including fees."),
    22894: _f(
        22894,
        "AlgoSpotRate",
        "PRICE",
        "FXGO Algo spot and forward trades: the spot rate, excluding fees.",
    ),
    # Algo / STP leg-level execution economics
    12606: _f(
        12606,
        "LegLeaves",
        "QTY",
        "Quantity open for further execution of this order's instrument leg.",
    ),
    22181: _f(
        22181,
        "LegCumQty",
        "QTY",
        "Cumulative quantity filled of this order's instrument leg.",
    ),
    22182: _f(
        22182,
        "LegLeavesQty",
        "QTY",
        "Quantity open for further execution of this order's instrument leg "
        "(0 once the order is Canceled or Rejected; otherwise LegQty(687) - "
        "LegCumQty(22181)).",
    ),
    22183: _f(22183, "LegText", "STRING", "Free-form text at the leg level."),
    22205: _f(
        22205,
        "LegSettlCurrAmt",
        "AMT",
        "Total amount due for the leg, in the settlement currency "
        "(LegSettlCurrency (675)). For NDFs: the settlement amount in the "
        "NDF settlement currency.",
    ),
    22206: _f(
        22206,
        "LegSettlCurrFxRate",
        "FLOAT",
        "Net average rate for a spot leg in an FX swap.",
    ),
    22208: _f(22208, "LegFixingSource", "STRING", "Fixing rate source for the leg (NDF)."),
    22826: _f(22826, "LegFixingDate", "LOCALMKTDATE", "Fixing date of the leg (NDF)."),
    22827: _f(
        22827,
        "LegLastSpotRate",
        "PRICE",
        "Spot rate of the last execution at the leg level, excluding fees. "
        "STP drop copy: the all-in spot rate including fees for the leg.",
    ),
    22831: _f(
        22831,
        "LegLastAllInPx",
        "PRICE",
        "All-in price of the last execution for the leg, including fees.",
    ),
    22832: _f(
        22832,
        "LegAvgSpotRate",
        "PRICE",
        "Average spot rate at which the currency pair in LegSymbol (600) is "
        "filled for the leg, excluding commission and fees.",
    ),
    22833: _f(
        22833,
        "LegAvgPx",
        "PRICE",
        "Average all-in price of all fills for the leg, including fees.",
    ),
    22834: _f(
        22834,
        "LegAvgAllInPx",
        "PRICE",
        "Average all-in price of all fills for the leg, including fees and "
        "forward points if applicable.",
    ),
    22835: _f(
        22835,
        "LegAvgForwardPoints",
        "PRICEOFFSET",
        "Average forward points for the leg; may be negative.",
    ),
    22836: _f(
        22836,
        "LegAvgCommission",
        "AMT",
        "Total average of the leg-level commission applied to the order.",
    ),
    22837: _f(
        22837,
        "LegFXTenor",
        "TENOR",
        "Settlement period for the leg (e.g. BROKEN, SPOT, TODAY, TOM, " "SP+1, T+3, 1W-3W, 1M-…).",
    ),
    22850: _f(
        22850,
        "LegLastAllInForward",
        "PRICEOFFSET",
        "Forward points including commission on the points, for the far leg " "of an FX swap.",
    ),
    22857: _f(
        22857,
        "LegLastSpotForwardPoints",
        "PRICE",
        "Price of the last execution for the leg, including forward points.",
    ),
    22859: _f(
        22859,
        "LegAvgSpotForwardPoints",
        "PRICE",
        "Average price/rate for the leg including forward points, excluding "
        "commission and fees.",
    ),
    22726: _f(22726, "LegCommission", "AMT", "Forward commission for the leg."),
    22727: _f(
        22727,
        "LegCommType",
        "CHAR",
        "Type of commission in LegCommission (22726).",
        {
            "1": "Amount per unit (per 1M USD; spread in PriceOffset form)",
            "3": "Absolute (total monetary amount)",
            "7": "Basis points (vs LastSpotRate (194) / LegLastSpotRate (22827))",
        },
    ),
    22728: _f(
        22728,
        "LegCommCurrency",
        "CURRENCY",
        "Currency of LegCommission (22726) when it differs from the deal currency.",
    ),
    # ------------------------------------------------------------------
    # FXGO STP drop copy — trade-level fields
    # ------------------------------------------------------------------
    989: _f(
        989,
        "SecondaryIndividualAllocID",
        "STRING",
        "Unique identifier assigned by the liquidity provider for each " "AllocAccount (79).",
    ),
    990: _f(990, "LegReportID", "STRING", "Trade identifier for the instrument leg."),
    1003: _f(
        1003,
        "TradeID",
        "STRING",
        "Identifier assigned by the sell-side to statically identify the "
        "trade; Bloomberg echoes the value as populated by the dealer.",
    ),
    1591: _f(
        1591,
        "LegQtyType",
        "INT",
        "Type of quantity specified in LegLastQty (1418); for FX only 0 " "(Units) is used.",
        {"0": "Units (shares, par, currency)", "1": "Contracts"},
    ),
    1600: _f(
        1600,
        "FIXEngineName",
        "STRING",
        "Name of the infrastructure component used for session-level "
        "communication (FIX engine / gateway product name).",
    ),
    1601: _f(1601, "FIXEngineVersion", "STRING", "Version of the FIX engine component."),
    1602: _f(1602, "FIXEngineVendor", "STRING", "Vendor of the FIX engine component."),
    1603: _f(
        1603,
        "ApplicationSystemName",
        "STRING",
        "Name of the application system generating FIX application messages "
        "(trading system, OMS or EMS).",
    ),
    1604: _f(1604, "ApplicationSystemVersion", "STRING", "Version of the application system."),
    1605: _f(1605, "ApplicationSystemVendor", "STRING", "Vendor of the application system."),
    1724: _f(
        1724,
        "OrderOrigination",
        "INT",
        "Where the order originated (MiFID II).",
        {
            "1": "Order received from a customer",
            "2": "Order received from within the firm",
            "3": "Order received from another broker-dealer",
            "4": "Order received from a customer or originated with the firm",
            "5": "Order received from a direct/sponsored access customer",
        },
    ),
    1844: _f(1844, "NoTradeAllocAmts", "NUMINGROUP", "Number of trade allocation amount entries."),
    1845: _f(
        1845,
        "TradeAllocAmtType",
        "STRING",
        "Type of the amount associated with a trade allocation.",
        {"PREM": "Premium amount", "UPFRNT": "Upfront payment"},
    ),
    1846: _f(1846, "TradeAllocAmt", "AMT", "The amount associated with a trade allocation."),
    1847: _f(
        1847,
        "TradeAllocCurrency",
        "CURRENCY",
        "Currency denomination of the trade allocation amount.",
    ),
    1937: _f(
        1937,
        "TradeContinuation",
        "INT",
        "Post-execution trade continuation or lifecycle event.",
        {"4": "Exercise (FX option exercise linked via TradeLinkID (820))"},
    ),
    2216: _f(
        2216,
        "MiscFeeRate",
        "PERCENTAGE",
        "Fee rate when MiscFeeAmt (137) is based on a percentage of trade "
        "quantity or a markup to price. For MiscFeeType(139)=8 (Markup): "
        "the price offset used to calculate the fee, as a raw decimal (an "
        "FX spot of 1.17936 marked up to 1.19 shows 0.01064).",
    ),
    2713: _f(
        2713,
        "MiscFeeDesc",
        "STRING",
        "Textual description of the fee type.",
        {
            "SPOTMARKUP": "Markup to spot",
            "FWDMARKUP": "Markup to forward points",
            "NEARLEGMARKUP": "Markup to forward points in the near leg of an FX swap",
            "FARLEGMARKUP": "Markup to forward points in the far leg of an FX swap",
            "PREMIUMMARKUP": "Markup to option premium",
        },
    ),
    22457: _f(
        22457,
        "MiscFeeLegRefID",
        "STRING",
        "Marks the fee entry as applying to a specific leg, referencing the " "leg's LegID (1788).",
    ),
    2796: _f(
        2796,
        "FXBenchmarkRateFix",
        "STRING",
        "FX benchmark rate fixing used in valuing the transaction, e.g. "
        "'London 16:00' or 'Tokyo 15:00'.",
    ),
    9102: _f(
        9102,
        "MarketType",
        "CHAR",
        "Type of market applicable to the trade.",
        {"N": "On shore", "O": "Off shore", "R": "Regular"},
    ),
    9123: _f(
        9123,
        "HedgeAmount",
        "AMT",
        "The trade amount associated with the option hedge (FX Options drop "
        "copy). Bloomberg-specific meaning of tag 9123 on FXGO STP.",
    ),
    9611: _f(
        9611,
        "NoteType",
        "STRING",
        "Type of the Bloomberg note entry.",
        {
            "C": "Customer note (dealer to client)",
            "D": "Dealer note (client to dealer)",
            "I": "Private/internal note (not sent to the counterparty)",
        },
    ),
    9676: _f(
        9676,
        "ContactEmailAddress",
        "STRING",
        "One or more email addresses, separated by commas.",
    ),
    22052: _f(
        22052,
        "LastMidPrice",
        "PRICE",
        "Winning dealer's quoted mid-price. FX Options drop copy: mid "
        "contract premium in PremiumCurrency (5830).",
    ),
    22053: _f(
        22053,
        "MidPriceType",
        "INT",
        "Price type of LastMidPrice (22052).",
        {
            "1": "Percentage (percent of par)",
            "2": "Per unit (FX Options)",
            "3": "Fixed amount (FX Options)",
        },
    ),
    22184: _f(
        22184,
        "ChatRoomID",
        "STRING",
        "The Bloomberg chat thread which resulted in the executed trade.",
    ),
    22215: _f(
        22215,
        "NoReferenceIDs",
        "NUMINGROUP",
        "Number of ReferenceID (22217) entries in the repeating group.",
    ),
    22216: _f(
        22216,
        "ReferenceIDType",
        "INT",
        "Source and type of ReferenceID (22217).",
        {
            "5": "BB # (initial identifier assigned as an option is created in RFQ)",
            "6": "Trade BB # (BB # assigned to the FX option upon execution)",
            "7": "Deal ID (identifier assigned to an FX Options trade)",
            "8": "OVML BB (OP number saved in OVML before the trade feeds RFQ/CNFO)",
        },
    ),
    22217: _f(22217, "ReferenceID", "STRING", "Reference identifier."),
    22450: _f(22450, "BasketItemCount", "INT", "Count of items in a basket of orders or trades."),
    22483: _f(
        22483,
        "CancelReason",
        "STRING",
        "Text entered by the client via the Bloomberg UI giving the reason "
        "for canceling the staged order (unsolicited cancels, "
        "ExecType(150)=4).",
    ),
    22484: _f(
        22484,
        "AutoOrdType",
        "INT",
        "Instruction to Bloomberg on how release of the order is to be routed.",
        {
            "0": "Auto-RFQ (inquiry submitted to selected price makers at best rate)",
            "2": "Auto-Broker Algo (Bloomberg applies the broker algorithm)",
            "3": "Auto-Front Office Order (routed to the central treasury desk)",
        },
    ),
    22515: _f(
        22515,
        "AutoExRuleInst",
        "CHAR",
        "Instructions for auto-execution.",
        {
            "y": "Auto-route (sent to price makers per AutoOrdType (22484))",
            "z": "Manual-route (staged for manual release)",
        },
    ),
    22546: _f(
        22546,
        "PartyIDSourceQualifier",
        "CHAR",
        "Further qualifies PartyIDSource(447)=D (Proprietary) when "
        "PartyRole(452)=56 (Acceptable counterparty).",
        {"2": "Broker code (also called deal code)"},
    ),
    22725: _f(
        22725,
        "TradeProcessingMethod",
        "INT",
        "Identifies a trade that was netted or merged into an FX swap "
        "(linked via a common ClOrdLinkID (583) or ListID (66)).",
    ),
    22908: _f(
        22908,
        "OrderGroupingMethod",
        "INT",
        "Grouping method the order originators would like applied to the " "orders in FXEM.",
        {"0": "No grouping (default)", "1": "Auto-Net", "2": "Auto-Batch"},
    ),
    22920: _f(
        22920,
        "AllocSettlCurrFxRate",
        "FLOAT",
        "FX rate used to compute AllocSettlCurrAmt (737) from Currency (15) "
        "to AllocSettlCurrency (736).",
    ),
    22921: _f(
        22921,
        "AllocSettlCurrFxRateCalc",
        "CHAR",
        "Whether AllocSettlCurrFxRate (22920) should be multiplied or divided.",
        {"D": "Divide", "M": "Multiply"},
    ),
    22952: _f(
        22952,
        "HEFFTemplateID",
        "STRING",
        "Hedge effective template ID for the MARS (Multi Asset Risk System) " "component.",
    ),
    22965: _f(
        22965,
        "ListTimeInForce",
        "CHAR",
        "Time in force for the entire list order.",
        {
            "0": "Day",
            "1": "Good Till Cancel (GTC; default)",
            "6": "Good Till Date (GTD; requires ListExpireDate/ListExpireTime)",
        },
    ),
    22966: _f(
        22966,
        "ListExpireDate",
        "LOCALMKTDATE",
        "Local market date when the list order expires (GTD).",
    ),
    22967: _f(
        22967,
        "ListExpireTime",
        "UTCTIMESTAMP",
        "UTC date and time when the list order expires (GTD).",
    ),
    22559: _f(
        22559,
        "AllocHedgeQty",
        "QTY",
        "Quantity of hedge allocated; may be negative if the allocation "
        "direction is opposite to the trade's Side (54).",
    ),
    22560: _f(
        22560,
        "AllocHedgePercent",
        "PERCENTAGE",
        "Percentage of hedge allocated; may be negative if the allocation "
        "direction is opposite to the trade's Side (54).",
    ),
    22567: _f(
        22567,
        "AllocPercent",
        "PERCENTAGE",
        "Percentage of notional allocated; may be negative if the "
        "allocation direction is opposite to the trade's Side (54).",
    ),
    22561: _f(
        22561,
        "LegAllocPercent",
        "PERCENTAGE",
        "Percentage of leg notional allocated; may be negative if opposite "
        "to the leg's LegSide (624).",
    ),
    22569: _f(
        22569,
        "LegAllocHedgeQty",
        "QTY",
        "Quantity of hedge allocated at the leg level; may be negative if "
        "opposite to the leg's LegSide (624).",
    ),
    22570: _f(
        22570,
        "LegAllocHedgePercent",
        "PERCENTAGE",
        "Percentage of hedge allocated at the leg level; may be negative if "
        "opposite to the leg's LegSide (624).",
    ),
    # ------------------------------------------------------------------
    # FXGO STP drop copy — FX options
    # ------------------------------------------------------------------
    1188: _f(1188, "Volatility", "FLOAT", "Volatility of the instrument."),
    1379: _f(1379, "LegVolatility", "FLOAT", "Volatility of the instrument leg."),
    1193: _f(
        1193,
        "SettlMethod",
        "STRING",
        "Settlement method for a contract or instrument (FX Options drop copy).",
        _CASH_PHYSICAL,
    ),
    2192: _f(
        2192,
        "LegSettlMethod",
        "CHAR",
        "Settlement method for the leg contract or instrument (FX Options " "drop copy).",
        _CASH_PHYSICAL,
    ),
    1194: _f(
        1194,
        "ExerciseStyle",
        "INT",
        "Type of exercise of a derivative security (FX Options drop copy).",
        _EXERCISE_STYLES,
    ),
    1420: _f(
        1420,
        "LegExerciseStyle",
        "INT",
        "Type of exercise of the leg derivative security (FX Options drop copy).",
        _EXERCISE_STYLES,
    ),
    1358: _f(
        1358,
        "LegPutOrCall",
        "INT",
        "Whether the leg option contract is a put or call.",
        {"0": "Put", "1": "Call", "100": "Other (cannot be determined)"},
    ),
    9034: _f(
        9034,
        "PutOrCallCurrency",
        "CURRENCY",
        "Currency of the put or call (ISO 4217).",
    ),
    22225: _f(
        22225,
        "LegPutOrCallCurrency",
        "CURRENCY",
        "Currency of the put or call at the leg level (ISO 4217).",
    ),
    1478: _f(
        1478,
        "StrikePriceDeterminationMethod",
        "INT",
        "How the strike price is determined at the point of option exercise.",
        {
            "3": "Strike set to average of underlying settlement price (Asian/Average)",
            "100": "Strike set to geometric average of underlying settlement price",
        },
    ),
    2186: _f(
        2186,
        "LegStrikePriceDeterminationMethod",
        "INT",
        "How the leg strike price is determined at the point of option exercise.",
        {
            "3": "Strike set to average of underlying settlement price (Asian/Average)",
            "100": "Strike set to geometric average of underlying settlement price",
        },
    ),
    1481: _f(
        1481,
        "UnderlyingPriceDeterminationMethod",
        "INT",
        "How the underlying price is determined at the point of option exercise.",
        {
            "1": "Regular (default)",
            "4": "Average value (Asian option)",
            "100": "Geometric average value (Asian option)",
        },
    ),
    2189: _f(
        2189,
        "LegUnderlyingPriceDeterminationMethod",
        "INT",
        "How the leg underlying price is determined at the point of option " "exercise.",
        {
            "4": "Average value (Asian option)",
            "100": "Geometric average value (Asian option)",
        },
    ),
    1482: _f(
        1482,
        "OptPayoutType",
        "INT",
        "Type of payout trigger for an in-the-money option (used for DCD " "options).",
        {"106": "Dual currency (redemption and interest paid per spot vs strike at maturity)"},
    ),
    2141: _f(
        2141,
        "StrategyType",
        "STRING",
        "Type of trade strategy (FX Options drop copy), e.g. ACCM "
        "(Accumulator), AVG (Average), and other codes per the spec's "
        "Strategy Conversion table.",
    ),
    2211: _f(
        2211,
        "LegStrategyType",
        "STRING",
        "Type of trade strategy at the leg level when multiple strategies "
        "are at work; legs of one strategy are tied together by "
        "LegStrategyGroup (22528).",
    ),
    22528: _f(
        22528,
        "LegStrategyGroup",
        "STRING",
        "Common value tying together the legs associated with the same "
        "strategy (e.g. butterfly or straddle), used with LegStrategyType "
        "(2211).",
    ),
    22541: _f(
        22541,
        "LegParentStrategyType",
        "STRING",
        "Parent strategy of the leg when different from LegStrategyType (2211).",
    ),
    6351: _f(
        6351,
        "StrategyPosition",
        "INT",
        "Position relative to the strategy.",
        {"0": "Same as strategy", "1": "Opposite to strategy"},
    ),
    22227: _f(
        22227,
        "LegStrategyPosition",
        "INT",
        "Position relative to the strategy, at the leg level.",
        {"0": "Same as strategy", "1": "Opposite to strategy"},
    ),
    22547: _f(
        22547,
        "BarrierDirection",
        "INT",
        "Qualifies StrategyType (2141) with the barrier direction.",
        _BARRIER_DIRECTION,
    ),
    22548: _f(
        22548,
        "LegBarrierDirection",
        "INT",
        "Qualifies LegStrategyType (2211) with the barrier direction.",
        _BARRIER_DIRECTION,
    ),
    22252: _f(
        22252,
        "OptionHashID",
        "STRING",
        "Bloomberg's option hash identifier, at the base strategy level.",
    ),
    22264: _f(
        22264,
        "LegOptionHashID",
        "STRING",
        "Bloomberg's FX option hash identifier at the leg level of a " "multileg trade.",
    ),
    1483: _f(
        1483,
        "NoComplexEvents",
        "NUMINGROUP",
        "Number of complex event entries (FX Options drop copy).",
    ),
    1484: _f(
        1484,
        "ComplexEventType",
        "INT",
        "Type of complex event (barrier / touch / accrual).",
        _COMPLEX_EVENT_TYPES,
    ),
    1486: _f(
        1486,
        "ComplexEventPrice",
        "PRICE",
        "Price at which the complex event takes effect; impact is "
        "determined by ComplexEventType (1484). Accumulators: the lower or "
        "upper boundary of the accrual range.",
    ),
    1487: _f(
        1487,
        "ComplexEventPriceBoundaryMethod",
        "INT",
        "Boundary condition for the event price relative to the underlying "
        "price when the event outcome takes effect.",
        {
            "1": "Less than ComplexEventPrice (1486)",
            "2": "Less than or equal to ComplexEventPrice (1486)",
            "3": "Equal to ComplexEventPrice (1486)",
            "4": "Greater than or equal to ComplexEventPrice (1486)",
            "5": "Greater than ComplexEventPrice (1486)",
        },
    ),
    1489: _f(
        1489,
        "ComplexEventPriceTimeType",
        "INT",
        "When the complex event outcome (payout or barrier action) takes effect.",
        _EVENT_PRICE_TIME,
    ),
    1490: _f(
        1490,
        "ComplexEventCondition",
        "INT",
        "Links a chain of complex events, describing the relationship " "between any two events.",
        _EVENT_CONDITION,
    ),
    22224: _f(22224, "ComplexRebate", "AMT", "Rebate associated with the complex event."),
    1491: _f(
        1491,
        "NoComplexEventDates",
        "NUMINGROUP",
        "Number of complex event date entries.",
    ),
    1492: _f(
        1492,
        "ComplexEventStartDate",
        "UTCDATEONLY",
        "Start date of the date range on which a complex event is effective "
        "(equal to the end date for single-day events such as Bermuda "
        "options).",
    ),
    1493: _f(
        1493,
        "ComplexEventEndDate",
        "UTCDATEONLY",
        "End date of the date range on which a complex event is effective.",
    ),
    2218: _f(
        2218,
        "NoLegComplexEvents",
        "NUMINGROUP",
        "Number of leg complex event entries (FX Options drop copy).",
    ),
    2219: _f(
        2219,
        "LegComplexEventType",
        "INT",
        "Type of leg complex event (barrier / touch / accrual).",
        _COMPLEX_EVENT_TYPES,
    ),
    2227: _f(
        2227,
        "LegComplexEventPrice",
        "PRICE",
        "Price at which the leg complex event takes effect; impact is "
        "determined by LegComplexEventType (2219).",
    ),
    2229: _f(
        2229,
        "LegComplexEventPriceBoundaryMethod",
        "INT",
        "Boundary condition for the leg event price relative to the "
        "underlying price when the event outcome takes effect.",
        {
            "1": "Less than LegComplexEventPrice (2227)",
            "2": "Less than or equal to LegComplexEventPrice (2227)",
            "3": "Equal to LegComplexEventPrice (2227)",
            "4": "Greater than or equal to LegComplexEventPrice (2227)",
            "5": "Greater than LegComplexEventPrice (2227)",
        },
    ),
    2231: _f(
        2231,
        "LegComplexEventPriceTimeType",
        "INT",
        "When the leg complex event outcome takes effect.",
        _EVENT_PRICE_TIME,
    ),
    2232: _f(
        2232,
        "LegComplexEventCondition",
        "INT",
        "Links a chain of leg complex events, describing the relationship "
        "between any two events.",
        _EVENT_CONDITION,
    ),
    22228: _f(22228, "LegComplexRebate", "AMT", "Rebate associated with the leg complex event."),
    2250: _f(
        2250,
        "NoLegComplexEventDates",
        "NUMINGROUP",
        "Number of leg complex event date entries.",
    ),
    2251: _f(
        2251,
        "LegComplexEventStartDate",
        "UTCDATEONLY",
        "Start date of the date range on which a leg complex event is effective.",
    ),
    2252: _f(
        2252,
        "LegComplexEventEndDate",
        "UTCDATEONLY",
        "End date of the date range on which a leg complex event is effective.",
    ),
    22617: _f(
        22617,
        "PivotPrice",
        "PRICE",
        "FX Pivot TARF: the pivot price (the 'Rate' field in the Bloomberg ticket).",
    ),
    22618: _f(
        22618,
        "InTheMoneyNotional",
        "AMT",
        "TARF strategies: the In-The-Money notional amount ('lower level "
        "notional' for Pivot TARF).",
    ),
    22619: _f(
        22619,
        "OutOfMoneyNotional",
        "AMT",
        "TARF strategies: the Out-Of-The-Money notional amount ('upper "
        "level notional' for Pivot TARF).",
    ),
    22620: _f(
        22620,
        "HighStrikePrice",
        "PRICE",
        "Dual Strike TARF: the Out-Of-The-Money strike price; other TARF "
        "strategies: the upper level strike price.",
    ),
    22621: _f(22621, "LegPivotPrice", "PRICE", "Pivot TARF: the pivot price at the leg level."),
    22622: _f(
        22622,
        "LegInTheMoneyNotional",
        "AMT",
        "TARF strategies: the In-The-Money notional amount at the leg level.",
    ),
    22623: _f(
        22623,
        "LegOutOfMoneyNotional",
        "AMT",
        "TARF strategies: the Out-Of-The-Money notional amount at the leg level.",
    ),
    22624: _f(
        22624,
        "LegHighStrikePrice",
        "AMT",
        "Dual Strike TARF: the Out-Of-The-Money strike price at the leg "
        "level; other TARF strategies: the upper level strike price.",
    ),
    22866: _f(
        22866,
        "StrikeOffset",
        "PRICEOFFSET",
        "Average Strike options: pre-determined value added to the strike " "upon expiration.",
    ),
    22867: _f(
        22867,
        "LegStrikeOffset",
        "PRICEOFFSET",
        "Average Strike options: pre-determined value added to the leg " "strike upon expiration.",
    ),
    22934: _f(
        22934,
        "AutoExpiryFlag",
        "BOOLEAN",
        "Whether exercise or expiry of the option is automatically "
        "triggered on the moneyness (ITM/ATM/OTM) of the option at "
        "maturity; when Y, the RateSource group is required.",
        {"Y": "Automatic", "N": "Manual intervention"},
    ),
    22226: _f(
        22226,
        "OptionExerciseDeliveryDate",
        "LOCALMKTDATE",
        "The delivery date on which the option settles.",
    ),
    22230: _f(
        22230,
        "LegOptionExerciseDeliveryDate",
        "LOCALMKTDATE",
        "The delivery date on which the leg option settles.",
    ),
    # Premium
    5020: _f(
        5020,
        "PremiumDeliveryDate",
        "LOCALMKTDATE",
        "Date on which the NetPremiumAmount (5844) is to be paid.",
    ),
    5830: _f(
        5830,
        "PremiumCurrency",
        "CURRENCY",
        "Currency of the premium in NetPremiumAmount (5844).",
    ),
    5844: _f(
        5844,
        "NetPremiumAmount",
        "AMT",
        "Net premium to be paid for the trade, in PremiumCurrency (5830); "
        "may be negative (received from the seller) regardless of Side (54).",
    ),
    22682: _f(
        22682,
        "PremiumSettlCurrFxRate",
        "FLOAT",
        "FX rate used to compute PremiumSettlCurrAmt (23004).",
    ),
    23004: _f(
        23004,
        "PremiumSettlCurrAmt",
        "AMT",
        "Total premium converted to PremiumSettlCurrency (23005).",
    ),
    23005: _f(
        23005,
        "PremiumSettlCurrency",
        "CURRENCY",
        "Currency of the converted total premium in PremiumSettlCurrAmt (23004).",
    ),
    23007: _f(
        23007,
        "LegPremium",
        "AMT",
        "Premium to be paid for this leg of the strategy; may be negative "
        "(received from the seller) regardless of LegSide (624).",
    ),
    22463: _f(
        22463,
        "LegPremiumDeliveryDate",
        "LOCALMKTDATE",
        "Date on which the LegPremium (23007) is to be paid.",
    ),
    22536: _f(
        22536,
        "LegPremiumCurrency",
        "CURRENCY",
        "Currency of the leg premium in LegPremium (23007).",
    ),
    22683: _f(
        22683,
        "LegPremiumSettlCurrFxRate",
        "FLOAT",
        "FX rate used to compute LegPremiumSettlCurrAmt (23003) (CNFO only).",
    ),
    23002: _f(
        23002,
        "LegPremiumSettlCurrency",
        "CURRENCY",
        "Currency of the converted leg premium (CNFO only).",
    ),
    23003: _f(
        23003,
        "LegPremiumSettlCurrAmt",
        "AMT",
        "Leg premium converted to LegPremiumSettlCurrency (23002) (CNFO only).",
    ),
    # Hedge
    6666: _f(
        6666,
        "HedgeDirection",
        "INT",
        "Side of the hedge (FX Options drop copy).",
        {"1": "Buy", "2": "Sell"},
    ),
    9015: _f(
        9015,
        "ExecDeltaHedge",
        "BOOLEAN",
        "Whether the trade is an exec-delta hedge.",
        {"Y": "Yes", "N": "No"},
    ),
    9016: _f(9016, "HedgeTradeType", "INT", "Hedge trade type.", _HEDGE_TRADE_TYPE),
    9657: _f(9657, "HedgeRate", "FLOAT", "FX rate at which the delta hedge trade was done."),
    22265: _f(22265, "HedgeCurrency", "CURRENCY", "The hedge currency (FX Options drop copy)."),
    22292: _f(
        22292,
        "HedgeSecurityID",
        "STRING",
        "Identifier of the hedge security when the security is traded on "
        "spread against a hedge (FX Options: the ISIN of the FX hedge "
        "security).",
    ),
    22293: _f(
        22293,
        "HedgeSecurityIDSource",
        "STRING",
        "Identifier source for HedgeSecurityID (22292).",
        _HEDGE_ID_SOURCE,
    ),
    22514: _f(
        22514, "HedgeSettlMethod", "STRING", "Settlement method for the hedge.", _CASH_PHYSICAL
    ),
    22656: _f(
        22656,
        "HedgeSettlCurrency",
        "CURRENCY",
        "Settlement currency of the hedge (required when the hedge is cash "
        "settled; same as SettlCurrency (120)).",
    ),
    22890: _f(
        22890,
        "CalculatedHedgeCurrency",
        "CURRENCY",
        "Currency opposite to HedgeCurrency (22265) per the pair in Symbol (55).",
    ),
    22891: _f(
        22891,
        "CalculatedHedgeAmount",
        "AMT",
        "Hedge amount denominated in CalculatedHedgeCurrency (22890).",
    ),
    22898: _f(
        22898,
        "HedgeUPICode",
        "STRING",
        "UPI (ISO 4914) of the hedge security.",
    ),
    22168: _f(
        22168,
        "LegPriceDelta",
        "FLOAT",
        "Rate of change of the leg derivative price with respect to the "
        "underlying price (FX Options drop copy).",
    ),
    22562: _f(
        22562,
        "LegHedgeAmount",
        "AMT",
        "Trade amount associated with the option hedge at the leg level.",
    ),
    22563: _f(
        22563,
        "LegHedgeCurrency",
        "CURRENCY",
        "Currency of the option-hedge trade amount at the leg level.",
    ),
    22677: _f(
        22677,
        "LegExecDeltaHedge",
        "BOOLEAN",
        "Whether the trade is an exec-delta hedge at the leg level.",
        {"Y": "Yes", "N": "No"},
    ),
    22678: _f(
        22678,
        "LegDeltaHedgeSide",
        "INT",
        "Side of the delta hedge at the leg level.",
        {"1": "Buy", "2": "Sell"},
    ),
    22679: _f(
        22679,
        "LegHedgeRate",
        "FLOAT",
        "FX rate at which the delta hedge trade was done, at the leg level.",
    ),
    22680: _f(
        22680,
        "LegHedgeTradeType",
        "INT",
        "Hedge trade type at the leg level.",
        _HEDGE_TRADE_TYPE,
    ),
    22681: _f(22681, "LegHedgeDate", "LOCALMKTDATE", "The hedge date at the leg level."),
    22861: _f(
        22861,
        "LegHedgeFixingDate",
        "UTCDATEONLY",
        "Fixing date for the option hedge at the leg level (cash-settled hedges).",
    ),
    22892: _f(
        22892,
        "LegCalculatedHedgeCurrency",
        "CURRENCY",
        "Currency opposite to LegHedgeCurrency (22563) per the pair in " "LegSymbol (600).",
    ),
    22893: _f(
        22893,
        "LegCalculatedHedgeAmount",
        "AMT",
        "Leg option-hedge amount denominated in LegCalculatedHedgeCurrency (22892).",
    ),
    22948: _f(
        22948,
        "LegHedgeSecurityID",
        "STRING",
        "ISIN of the FX hedge security at the leg level.",
    ),
    22949: _f(
        22949,
        "LegHedgeSecurityIDSource",
        "STRING",
        "Identifier source for LegHedgeSecurityID (22948).",
        _HEDGE_ID_SOURCE,
    ),
    22950: _f(
        22950,
        "LegHedgeSettlMethod",
        "STRING",
        "Settlement method for the hedge at the leg level.",
        _CASH_PHYSICAL,
    ),
    22951: _f(
        22951,
        "LegHedgeUPICode",
        "STRING",
        "UPI (ISO 4914) of the leg hedge security.",
    ),
    # Deposits / dual currency deposit options
    1950: _f(
        1950,
        "CouponDayCount",
        "INT",
        "Day count convention used in interest calculations (FX deposits).",
        _COUPON_DAY_COUNTS,
    ),
    1993: _f(
        1993,
        "UnderlyingCouponDayCount",
        "INT",
        "Day count convention for the term deposit underlying a dual " "currency deposit option.",
        _COUPON_DAY_COUNTS,
    ),
    2042: _f(
        2042,
        "UnderlyingInterestAccrualDate",
        "LOCALMKTDATE",
        "Date interest starts accruing (issue date) for the term deposit of "
        "a dual currency deposit option.",
    ),
    2614: _f(
        2614,
        "UnderlyingNotional",
        "AMT",
        "Notional amount of the term deposit (dual currency deposit options).",
    ),
    2615: _f(
        2615,
        "UnderlyingNotionalCurrency",
        "CURRENCY",
        "Currency of the notional amount in UnderlyingNotional (2614).",
    ),
    7220: _f(
        7220,
        "PortfolioName",
        "STRING",
        "Portfolio name set up by an FX user via Bloomberg's PRTU function.",
    ),
    # Payments (FX Bank Notes)
    40212: _f(40212, "NoPayments", "NUMINGROUP", "Number of payment entries."),
    40213: _f(
        40213,
        "PaymentType",
        "INT",
        "Type of payment.",
        {"99": "Other (used for FX Bank Notes)"},
    ),
    40216: _f(
        40216,
        "PaymentCurrency",
        "CURRENCY",
        "Currency in which PaymentAmount (40217) is denominated (ISO 4217).",
    ),
    40217: _f(40217, "PaymentAmount", "AMT", "The total payment amount."),
    40222: _f(40222, "PaymentDateAdjusted", "LOCALMKTDATE", "The adjusted payment date."),
    41304: _f(
        41304,
        "PaymentLegRefID",
        "STRING",
        "Identifies the instrument leg this payment applies to, referencing "
        "the leg's LegID (1788).",
    ),
    # Option exercise dates (FIX Latest 41xxx tags)
    41122: _f(
        41122,
        "OptionExerciseFrequencyPeriod",
        "INT",
        "Time unit multiplier for the frequency of exercise dates "
        "(Accumulator / TARF strategies).",
    ),
    41123: _f(
        41123,
        "OptionExerciseFrequencyUnit",
        "STRING",
        "Time unit associated with the frequency of exercise dates.",
        _EXERCISE_FREQ_UNITS,
    ),
    41124: _f(
        41124,
        "OptionExerciseStartDateUnadjusted",
        "LOCALMKTDATE",
        "Unadjusted start date for calculating periodic exercise dates.",
    ),
    41132: _f(
        41132,
        "OptionExerciseFirstDateUnadjusted",
        "LOCALMKTDATE",
        "The unadjusted first exercise date.",
    ),
    41133: _f(
        41133,
        "OptionExerciseLastDateUnadjusted",
        "LOCALMKTDATE",
        "The unadjusted last exercise date.",
    ),
    41135: _f(41135, "OptionExerciseLatestTime", "LOCALMKTTIME", "The latest exercise time."),
    41136: _f(
        41136,
        "OptionExerciseTimeBusinessCenter",
        "STRING",
        "Business center determining the locale for the option exercise "
        "time, e.g. 'GBLO' (FpML business-center codes).",
    ),
    41152: _f(
        41152,
        "NoOptionExerciseExpirationDates",
        "NUMINGROUP",
        "Number of option exercise expiration dates (only one instance is " "supported).",
    ),
    41153: _f(
        41153,
        "OptionExerciseExpirationDate",
        "LOCALMKTDATE",
        "An adjusted fixed option exercise expiration date.",
    ),
    41154: _f(
        41154,
        "OptionExerciseExpirationDateType",
        "INT",
        "Type of option exercise expiration date.",
        {"1": "Adjusted"},
    ),
    41497: _f(
        41497,
        "LegOptionExerciseFrequencyPeriod",
        "INT",
        "Time unit multiplier for the frequency of leg exercise dates.",
    ),
    41498: _f(
        41498,
        "LegOptionExerciseFrequencyUnit",
        "STRING",
        "Time unit associated with the frequency of leg exercise dates.",
        _EXERCISE_FREQ_UNITS,
    ),
    41499: _f(
        41499,
        "LegOptionExerciseStartDateUnadjusted",
        "LOCALMKTDATE",
        "Unadjusted start date for calculating periodic leg exercise dates.",
    ),
    41507: _f(
        41507,
        "LegOptionExerciseFirstDateUnadjusted",
        "LOCALMKTDATE",
        "The unadjusted first leg exercise date.",
    ),
    41508: _f(
        41508,
        "LegOptionExerciseLastDateUnadjusted",
        "LOCALMKTDATE",
        "The unadjusted last leg exercise date.",
    ),
    41510: _f(
        41510,
        "LegOptionExerciseLatestTime",
        "LOCALMKTTIME",
        "The latest leg exercise time.",
    ),
    41511: _f(
        41511,
        "LegOptionExerciseTimeBusinessCenter",
        "STRING",
        "Business center determining the locale for the leg option exercise "
        "time, e.g. 'GBLO' (FpML business-center codes).",
    ),
    # STP LegPreAllocGrp block-trade indicator (a different tag from the
    # FIXBOOK leg financing indicator 22417, which Bloomberg also names
    # LegTrdType).
    22247: _f(
        22247,
        "LegTrdType",
        "INT",
        "Whether the swap leg qualifies as a block trade as determined by "
        "the regulators; FX sends only 47 (BMTF/BTFE trades).",
        {"47": "Financing transaction"},
    ),
}
