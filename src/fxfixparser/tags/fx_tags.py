"""FX-specific custom tag definitions based on LiquidityFX (LFX) FIX specification."""

from fxfixparser.core.field import FixFieldDefinition

# Supported tenor codes from LFX specification section 11.9
LFX_TENOR_VALUES = {
    "SPOT": "Spot",
    "ONI": "Overnight",
    "SNX": "Spot Next",
    "TOD": "Today",
    "TOM": "Tomorrow",
    "TNX": "Tomorrow Next",
    "D2": "Spot + 2 Days",
    "D3": "Spot + 3 Days",
    "D4": "Spot + 4 Days",
    "W1": "1 Week",
    "W2": "2 Weeks",
    "W3": "3 Weeks",
    "M1": "1 Month",
    "M2": "2 Months",
    "M3": "3 Months",
    "M4": "4 Months",
    "M5": "5 Months",
    "M6": "6 Months",
    "M7": "7 Months",
    "M8": "8 Months",
    "M9": "9 Months",
    "M10": "10 Months",
    "M11": "11 Months",
    "M15": "15 Months",
    "M18": "18 Months",
    "M21": "21 Months",
    "Y1": "1 Year",
    "Y2": "2 Years",
    "Y3": "3 Years",
    "Y4": "4 Years",
    "Y5": "5 Years",
    "Y6": "6 Years",
    "Y7": "7 Years",
    "Y8": "8 Years",
    "Y9": "9 Years",
    "Y10": "10 Years",
    "Y15": "15 Years",
    "Y20": "20 Years",
    "Y25": "25 Years",
    "Y30": "30 Years",
    "JAN": "Third Wednesday of next January (IMM)",
    "FEB": "Third Wednesday of next February (IMM)",
    "MAR": "Third Wednesday of next March (IMM)",
    "APR": "Third Wednesday of next April (IMM)",
    "MAY": "Third Wednesday of next May (IMM)",
    "JUN": "Third Wednesday of next June (IMM)",
    "JUL": "Third Wednesday of next July (IMM)",
    "AUG": "Third Wednesday of next August (IMM)",
    "SEP": "Third Wednesday of next September (IMM)",
    "OCT": "Third Wednesday of next October (IMM)",
    "NOV": "Third Wednesday of next November (IMM)",
    "DEC": "Third Wednesday of next December (IMM)",
    "ME1": "Last day of current month",
    "ME2": "Last day of next month",
    "ME3": "Last day of current month + 2 months",
    "ME4": "Last day of current month + 3 months",
    "ME5": "Last day of current month + 4 months",
    "ME6": "Last day of current month + 5 months",
    "ME7": "Last day of current month + 6 months",
    "ME8": "Last day of current month + 7 months",
    "ME9": "Last day of current month + 8 months",
    "ME10": "Last day of current month + 9 months",
    "ME11": "Last day of current month + 10 months",
    "ME12": "Last day of current month + 11 months",
}

FX_CUSTOM_TAGS: list[FixFieldDefinition] = [
    # ============================================================================
    # Standard FIX tags not in FIX 4.4 XML but used in repeating groups
    # (FIX 5.0 / FIX 5.0 SP2 additions)
    # ============================================================================
    FixFieldDefinition(685, "LegOrderQty", "QTY", "Order quantity for a leg of a multi-leg instrument."),
    FixFieldDefinition(1362, "NoFills", "NUMINGROUP", "Number of fill entries in the Fills repeating group."),
    FixFieldDefinition(1363, "FillExecID", "STRING", "Unique identifier of the fill as assigned by the sell-side."),
    FixFieldDefinition(1364, "FillPx", "PRICE", "Price of this fill."),
    FixFieldDefinition(1365, "FillQty", "QTY", "Quantity bought/sold on this fill."),
    FixFieldDefinition(1443, "FillLiquidityInd", "INT", "Indicator to identify whether this fill was a result of a liquidity provider providing or taking liquidity."),

    # ============================================================================
    # LiquidityFX (LFX) Custom Tags - 8000 Range
    # Based on smartTrade LiquidityFX Distribution FIX ROE v4.2.78.0-GA
    # ============================================================================

    # MassQuote entry identifiers
    FixFieldDefinition(8000, "BidEntryID", "STRING", "Uniquely identifies the bid quote in a MassQuote message."),
    FixFieldDefinition(8001, "OfferEntryID", "STRING", "Uniquely identifies the offer quote in a MassQuote message."),

    # FX Swap settlement types (tenors)
    FixFieldDefinition(8004, "SettlType2", "STRING", "FX Swap: Far Leg Tenor. See Supported Tenor Codes for possible values.", LFX_TENOR_VALUES),

    # FX Swap spot rates for far leg
    FixFieldDefinition(8011, "BidSpotRate2", "PRICE", "FX Swap: Bid entry spot rate of the far leg."),
    FixFieldDefinition(8012, "OfferSpotRate2", "PRICE", "FX Swap: Offer entry spot rate of the far leg."),

    # FX Swap sizes for far leg
    FixFieldDefinition(8013, "BidSize2", "QTY", "FX Swap: Size of the far leg (bid entry/quote)."),
    FixFieldDefinition(8014, "OfferSize2", "QTY", "FX Swap: Size of the far leg (offer entry/quote)."),

    # FX Swap settlement dates (MassQuote)
    FixFieldDefinition(8015, "BidSettlDate", "LOCALMKTDATE", "Settlement date for the bid quote, format YYYYMMDD. FX Swap: refers to the near leg."),
    FixFieldDefinition(8016, "BidSettlDate2", "LOCALMKTDATE", "FX Swap: Settlement date for the far leg of the bid quote, format YYYYMMDD."),
    FixFieldDefinition(8017, "OfferSettlDate", "LOCALMKTDATE", "Settlement date for the offer quote, format YYYYMMDD. FX Swap: refers to the near leg."),
    FixFieldDefinition(8018, "OfferSettlDate2", "LOCALMKTDATE", "FX Swap: Settlement date for the far leg of the offer quote, format YYYYMMDD."),

    # FX Swap all-in prices for far leg
    FixFieldDefinition(8019, "BidPx2", "PRICE", "FX Swap: The all-in price of the bid entry's far leg."),
    FixFieldDefinition(8020, "OfferPx2", "PRICE", "FX Swap: The all-in price of the offer entry's far leg."),

    # Quote currencies
    FixFieldDefinition(8021, "BidCurrency", "CURRENCY", "Currency of the bid quote."),
    FixFieldDefinition(8022, "OfferCurrency", "CURRENCY", "Currency of the offer quote."),

    # ============================================================================
    # LFX Custom Tags - 1000 Range (Market Data & Swap Points)
    # ============================================================================

    # Forward market data components (per MD entry)
    FixFieldDefinition(1026, "MDEntrySpotRate", "PRICE", "Underlying spot rate for this market data entry. In forward market data, this is the spot component of the all-in forward price (MDEntryPx)."),
    FixFieldDefinition(1027, "MDEntryForwardPoints", "PRICEOFFSET", "Forward points for this market data entry. The difference between the all-in forward price (MDEntryPx) and the spot rate (MDEntrySpotRate)."),

    # Swap points
    FixFieldDefinition(1065, "BidSwapPoints", "PRICEOFFSET", "FX Swap: Swap points of the bid entry (price difference between the far leg and the near one)."),
    FixFieldDefinition(1066, "OfferSwapPoints", "PRICEOFFSET", "FX Swap: Swap points of the offer entry (price difference between the far leg and the near one)."),

    # ============================================================================
    # LFX Custom Tags - 9000 Range (Market Data & Execution)
    # ============================================================================

    # Market Data Request size tiers
    FixFieldDefinition(9000, "NoRequestedSize", "NUMINGROUP", "Number of size tiers requested for tiered market data quotes."),
    FixFieldDefinition(9001, "RequestedSize", "QTY", "The size of the quote tier for tiered market data."),

    # Forward Rolls
    FixFieldDefinition(9011, "ClRootOrderID", "STRING", "Forward Rolls: ID of the spot order to roll."),

    # NDF/NDS maturity
    FixFieldDefinition(9044, "MaturityDate2", "LOCALMKTDATE", "For NDS, fixing date expressed as YYYYMMDD of the far leg."),

    # Execution Report - Swap leg prices and quantities
    FixFieldDefinition(9091, "LastPx2", "PRICE", "For Swap, LastPx (fill price) of the far leg."),
    FixFieldDefinition(9092, "LastQty2", "QTY", "For swaps, amount of the far leg for this fill."),
    FixFieldDefinition(9093, "LeavesQty2", "QTY", "For swap, quantity opened for execution of far leg."),
    FixFieldDefinition(9094, "CumQty2", "QTY", "FX Swaps: Filled quantity of the far leg for this execution."),
    FixFieldDefinition(9095, "LastSpotRate2", "PRICE", "For Swap, LastSpotRate of the far leg."),

    # Market Data timestamps
    FixFieldDefinition(9122, "MDEntryOrigTime", "UTCTIMEONLY", "The UTC time received from venue HH:mm:ss.SSS. Only available when no aggregation (AggregatedBook=N)."),
    FixFieldDefinition(9123, "MDEntryOrigDate", "UTCDATEONLY", "The UTC date received from venue YYYYMMDD. Only available when no aggregation (AggregatedBook=N)."),

    # Fixing orders
    FixFieldDefinition(9300, "FixingSourceID", "STRING", "ID of the fixing source for fixing orders."),
    FixFieldDefinition(9301, "FixingTime", "UTCTIMESTAMP", "The UTC date/time for fixing orders, format YYYYMMDD-HH:mm:ss.SSS."),

    # Regulatory
    FixFieldDefinition(9400, "RegulationType", "STRING", "Type of regulated venue. Supported values: SEF (Swap Execution Facility under US regulation), MTF (Multilateral Trading Facility under EU MIFID2 regulation), XOFF (all other cases).", {
        "SEF": "Swap Execution Facility (US)",
        "MTF": "Multilateral Trading Facility (EU MIFID2)",
        "XOFF": "Off-exchange/Other",
    }),

    # ============================================================================
    # LFX Custom Tags - 10000 Range (UTI/Regulatory)
    # ============================================================================
    FixFieldDefinition(10002, "UTIPrefix", "STRING", "Unique Trade Id prefix."),
    FixFieldDefinition(10003, "UTI", "STRING", "Unique Trade Id."),
    FixFieldDefinition(10011, "IsSEFTrade", "BOOLEAN", "Whether order is traded on SEF or off SEF facility."),

    # ============================================================================
    # LFX Custom Tags - 11000 Range (Allocations)
    # ============================================================================
    FixFieldDefinition(11001, "RequestType", "CHAR", "Indicates that this report refers to a multileg QuoteRequest. Value: M = MULTILEG.", {
        "M": "Multileg",
    }),
    FixFieldDefinition(11003, "AllocationID", "STRING", "Client ID for the pre-allocation group."),
    FixFieldDefinition(11078, "C_NoAllocs", "NUMINGROUP", "Repeating group; number of pre-allocations."),
    FixFieldDefinition(11079, "C_AllocAccount", "STRING", "Account to which this allocation leg should be allocated."),
    FixFieldDefinition(11467, "C_IndividualAllocID", "STRING", "Client identifier for this allocation leg."),
    FixFieldDefinition(11080, "C_AllocQty", "QTY", "Quantity to be allocated. Should be positive."),
    FixFieldDefinition(11054, "C_AllocSide", "CHAR", "Side of this allocation leg, relative to the side of the future order.", {
        "B": "AS_DEFINED (same side)",
        "C": "OPPOSITE (opposite side)",
        "U": "UNDISCLOSED",
    }),
    FixFieldDefinition(11063, "C_AllocSettlType", "STRING", "Swaps allocations only: tenor of this allocation leg.", LFX_TENOR_VALUES),
    FixFieldDefinition(11064, "C_AllocSettlDate", "LOCALMKTDATE", "Swaps allocations only: value date of this allocation leg, format YYYYMMDD."),

    # Leg allocations
    FixFieldDefinition(11670, "C_NoLegAllocs", "NUMINGROUP", "Number of allocations for this leg."),
    FixFieldDefinition(11671, "C_LegAllocAccount", "STRING", "Allocation account for this leg."),
    FixFieldDefinition(11672, "C_LegIndividualAllocID", "STRING", "ID of this allocation leg."),
    FixFieldDefinition(11673, "C_LegAllocQty", "QTY", "Quantity to allocate for this leg."),
    FixFieldDefinition(11654, "C_LegAllocSide", "CHAR", "Side of this allocation leg.", {
        "B": "AS_DEFINED (same side as the leg)",
        "C": "OPPOSITE (opposite side to the leg)",
    }),

    # ============================================================================
    # FX-specific tags (5700 range) - Generic FX extensions
    # ============================================================================
    FixFieldDefinition(5700, "FXCurrencyPair", "STRING", "FX currency pair. The pair being traded in standard format (e.g., EURUSD, USDJPY)."),
    FixFieldDefinition(5701, "BaseCurrency", "CURRENCY", "Base currency of the pair. The first currency in the pair (e.g., EUR in EUR/USD)."),
    FixFieldDefinition(5702, "QuoteCurrency", "CURRENCY", "Quote/Terms currency of the pair. The second currency in the pair (e.g., USD in EUR/USD)."),
    FixFieldDefinition(5703, "ValueDate", "LOCALMKTDATE", "Value date for FX trade. The date when currencies are exchanged (settlement date)."),
    FixFieldDefinition(5704, "FarValueDate", "LOCALMKTDATE", "Far leg value date for swap. Settlement date for the second leg of an FX Swap."),
    FixFieldDefinition(5705, "NearLegQty", "QTY", "Near leg quantity for swap. The notional amount for the first leg of an FX Swap."),
    FixFieldDefinition(5706, "FarLegQty", "QTY", "Far leg quantity for swap. The notional amount for the second leg of an FX Swap."),
    FixFieldDefinition(5707, "SwapPoints", "PRICEOFFSET", "Swap points. Forward points representing the interest rate differential between currencies."),
    FixFieldDefinition(5708, "AllInRate", "PRICE", "All-in rate including forward points. The complete forward exchange rate (Spot + Forward Points)."),
    FixFieldDefinition(5709, "NDFFixingDate", "LOCALMKTDATE", "NDF fixing date. The date when the NDF fixing rate is determined."),
    FixFieldDefinition(5710, "NDFFixingRate", "PRICE", "NDF fixing rate. The official exchange rate used to calculate NDF settlement amount."),
    FixFieldDefinition(5711, "NDFFixingSource", "STRING", "NDF fixing rate source. The official source for the NDF fixing rate (e.g., WMR, BFIX)."),
    FixFieldDefinition(5712, "TenorValue", "STRING", "Tenor value. Standardized tenor code for the trade.", LFX_TENOR_VALUES),
    FixFieldDefinition(5713, "FarTenorValue", "STRING", "Far leg tenor value for swap. Tenor code for the second leg of an FX Swap.", LFX_TENOR_VALUES),

    # ============================================================================
    # Venue-specific tags (5800 range)
    # ============================================================================
    FixFieldDefinition(5800, "VenueTradeID", "STRING", "Venue-specific trade ID. Unique trade identifier assigned by the execution venue."),
    FixFieldDefinition(5801, "VenueOrderID", "STRING", "Venue-specific order ID. Unique order identifier assigned by the execution venue."),
    FixFieldDefinition(5802, "VenueQuoteID", "STRING", "Venue-specific quote ID. Unique quote identifier assigned by the execution venue."),
    FixFieldDefinition(5803, "VenueName", "STRING", "Trading venue name. Name of the platform where the trade was executed."),
    FixFieldDefinition(5804, "VenueTimestamp", "UTCTIMESTAMP", "Venue timestamp. Timestamp assigned by the venue for the event."),

    # ============================================================================
    # Counterparty tags (5900 range)
    # ============================================================================
    FixFieldDefinition(5900, "CounterpartyID", "STRING", "Counterparty identifier. Unique ID of the trading counterparty."),
    FixFieldDefinition(5901, "CounterpartyName", "STRING", "Counterparty name. Legal name of the trading counterparty."),
    FixFieldDefinition(5902, "CounterpartyLEI", "STRING", "Counterparty LEI code. Legal Entity Identifier of the counterparty."),

    # ============================================================================
    # Regulatory tags (6000 range)
    # ============================================================================
    FixFieldDefinition(6000, "TradeReportID", "STRING", "Trade report identifier. Unique ID for regulatory trade reporting."),
    FixFieldDefinition(6001, "RegulatoryReportType", "INT", "Regulatory report type. Indicates the type of regulatory report."),
    FixFieldDefinition(6002, "RegulatoryUTI", "STRING", "Unique Transaction Identifier for EMIR/MiFID regulatory reporting."),
    FixFieldDefinition(6003, "USI", "STRING", "Unique Swap Identifier for Dodd-Frank reporting."),

    # ============================================================================
    # Options-specific tags (standard FIX but FX-relevant)
    # ============================================================================
    FixFieldDefinition(201, "PutOrCall", "INT", "Put or call indicator. For FX Options, indicates whether option is a put or call on the base currency.", {
        "0": "Put", "1": "Call",
    }),
    FixFieldDefinition(202, "StrikePrice", "PRICE", "Strike price for option. The exchange rate at which the option can be exercised."),
    FixFieldDefinition(205, "MaturityDay", "DAYOFMONTH", "Maturity day of month. Day component of option expiry date."),
    FixFieldDefinition(200, "MaturityMonthYear", "MONTHYEAR", "Maturity month/year. Month and year of option expiry (format: YYYYMM)."),
    FixFieldDefinition(541, "MaturityDate", "LOCALMKTDATE", "Maturity date. Full expiry date for options or fixing date for NDF."),
    FixFieldDefinition(223, "CouponRate", "PERCENTAGE", "Coupon rate. Interest rate for fixed income instruments."),
    FixFieldDefinition(231, "ContractMultiplier", "FLOAT", "Contract multiplier. Multiplier to convert price to contract value (e.g., lot size)."),
    FixFieldDefinition(206, "OptAttribute", "CHAR", "Option attribute. Additional option characteristic (e.g., American vs European exercise)."),
    FixFieldDefinition(207, "SecurityExchange", "EXCHANGE", "Security exchange. Exchange or market where the instrument trades (e.g., CME for FX Futures)."),

    # ============================================================================
    # Additional standard FIX tags commonly used in FX
    # ============================================================================
    FixFieldDefinition(423, "PriceType", "INT", "Price type. How the price is expressed.", {
        "1": "Percentage", "2": "PerUnit", "3": "FixedAmount",
        "4": "Discount", "5": "Premium", "6": "Spread",
        "7": "TEDPrice", "8": "TEDYield", "9": "Yield",
        "10": "FixedCabinetTradePrice", "11": "VariableCabinetTradePrice",
    }),
    FixFieldDefinition(424, "GTBookingInst", "INT", "GT booking instruction. How to book Good-Till orders."),
    FixFieldDefinition(528, "OrderCapacity", "CHAR", "Order capacity. MIFID2 Trading capacity.", {
        "A": "Agency (AOTC in MIFID2)",
        "G": "Proprietary",
        "I": "Individual",
        "P": "Principal (DEAL in MIFID2)",
        "R": "RisklessPrincipal (MTCH in MIFID2)",
        "W": "AgentForOtherMember",
    }),
    FixFieldDefinition(529, "OrderRestrictions", "MULTIPLEVALUESTRING", "Order restrictions. Special handling instructions."),
    FixFieldDefinition(582, "CustOrderCapacity", "INT", "Customer order capacity. Capacity of the customer placing the order."),
    FixFieldDefinition(851, "LastLiquidityInd", "INT", "Last liquidity indicator. Indicates if the execution added or removed liquidity.", {
        "1": "AddedLiquidity", "2": "RemovedLiquidity", "3": "LiquidityRoutedOut",
    }),

    # ============================================================================
    # MIFID2 Regulatory Fields
    # ============================================================================
    FixFieldDefinition(2376, "PartyRoleQualifier", "INT", "Party role qualifier for MIFID2.", {
        "22": "Algorithm (for MIFID2 ExecutionWithinFirm)",
        "24": "Natural person (for MIFID2 Investment decision within firm)",
    }),
    FixFieldDefinition(2668, "NoTrdRegPublications", "NUMINGROUP", "Number of regulatory publication entries."),
    FixFieldDefinition(2669, "TrdRegPublicationType", "INT", "MIFID2 publication type.", {
        "0": "Pre-trade transparency waiver",
        "1": "Post-trade deferral",
        "2": "Exempt from publication",
    }),
    FixFieldDefinition(2670, "TrdRegPublicationReason", "INT", "MIFID2 publication reason.", {
        "6": "Deferral due to Large in Scale (LIS) threshold",
        "7": "Deferral due to illiquid instrument",
        "8": "Deferral due to Size Specific to Instrument (SSTI) threshold",
        "12": "Exempted due to ESCB policy transaction",
    }),
    FixFieldDefinition(768, "NoTrdRegTimestamps", "NUMINGROUP", "Number of regulatory timestamp entries."),
    FixFieldDefinition(769, "TrdRegTimestamp", "UTCTIMESTAMP", "Regulatory timestamp, format YYYYMMDD-HH:mm:ss.SSS."),
    FixFieldDefinition(770, "TrdRegTimestampType", "INT", "Regulatory timestamp type.", {
        "2": "Time In",
        "3": "Time Out",
    }),
    FixFieldDefinition(2593, "NoOrderAttributes", "NUMINGROUP", "Number of order attribute entries."),
    FixFieldDefinition(2594, "OrderAttributeType", "INT", "Order attribute type.", {
        "3": "Risk reduction order",
    }),
    FixFieldDefinition(2595, "OrderAttributeValue", "CHAR", "Order attribute value.", {
        "Y": "True (Risk Decreasing)",
        "N": "False (Risk Increasing)",
    }),
]
