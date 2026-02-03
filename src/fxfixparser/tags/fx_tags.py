"""FX-specific custom tag definitions."""

from fxfixparser.core.field import FixFieldDefinition

FX_CUSTOM_TAGS: list[FixFieldDefinition] = [
    # Smart Trade venue-specific tags (8000 range)
    FixFieldDefinition(8004, "FarLegSettlType", "STRING", "Far leg settlement type for FX Swap. Specifies when the second leg of a swap settles (e.g., TOM=Tomorrow, 1M=1 Month). Combined with near leg (tag 63) defines the swap tenor.", {
        "TOD": "Today", "TOM": "Tomorrow", "SPOT": "Spot", "SN": "Spot Next",
        "1W": "1 Week", "2W": "2 Weeks", "3W": "3 Weeks",
        "1M": "1 Month", "2M": "2 Months", "3M": "3 Months",
        "4M": "4 Months", "5M": "5 Months", "6M": "6 Months",
        "7M": "7 Months", "8M": "8 Months", "9M": "9 Months",
        "10M": "10 Months", "11M": "11 Months", "1Y": "1 Year",
        "2Y": "2 Years", "3Y": "3 Years", "BD": "Broken Date",
    }),
    FixFieldDefinition(8005, "NearLegSettlType", "STRING", "Near leg settlement type for FX Swap. Specifies when the first leg of a swap settles. Usually TOD, TOM, or SPOT.", {
        "TOD": "Today", "TOM": "Tomorrow", "SPOT": "Spot", "SN": "Spot Next",
        "1W": "1 Week", "2W": "2 Weeks", "3W": "3 Weeks",
        "1M": "1 Month", "2M": "2 Months", "3M": "3 Months",
        "BD": "Broken Date",
    }),
    FixFieldDefinition(8006, "FarLegSettlDate", "LOCALMKTDATE", "Far leg settlement date. Explicit value date for the second leg of an FX Swap. Format: YYYYMMDD."),
    FixFieldDefinition(8007, "NearLegSettlDate", "LOCALMKTDATE", "Near leg settlement date. Explicit value date for the first leg of an FX Swap. Format: YYYYMMDD."),
    FixFieldDefinition(8008, "FarLegAllInRate", "PRICE", "Far leg all-in rate. The complete exchange rate for the far leg including forward points (Spot Rate + Forward Points)."),
    FixFieldDefinition(8009, "NearLegAllInRate", "PRICE", "Near leg all-in rate. The complete exchange rate for the near leg (usually the spot rate for standard swaps)."),
    FixFieldDefinition(8010, "SwapPoints", "PRICEOFFSET", "Swap points (forward points). The interest rate differential between two currencies expressed in pips. Positive = base currency has lower interest rate."),
    FixFieldDefinition(8011, "NearLegBidAllInRate", "PRICE", "Near leg bid all-in rate. The complete bid exchange rate for the near leg of a swap (Spot + Near Leg Forward Points)."),
    FixFieldDefinition(8012, "NearLegOfferAllInRate", "PRICE", "Near leg offer all-in rate. The complete offer exchange rate for the near leg of a swap (Spot + Near Leg Forward Points)."),
    FixFieldDefinition(8013, "NearLegBidSize", "QTY", "Near leg bid size. The quantity available at the near leg bid rate."),
    FixFieldDefinition(8014, "NearLegOfferSize", "QTY", "Near leg offer size. The quantity available at the near leg offer rate."),
    FixFieldDefinition(8015, "StreamID", "STRING", "Streaming quote identifier. Unique ID for a streaming price feed, used to match execution to the quoted price."),
    FixFieldDefinition(8016, "NearLegBidForwardPoints", "PRICEOFFSET", "Near leg bid forward points. Forward points for the near leg bid rate."),
    FixFieldDefinition(8017, "NearLegOfferForwardPoints", "PRICEOFFSET", "Near leg offer forward points. Forward points for the near leg offer rate."),
    FixFieldDefinition(8018, "FarLegSettlDate", "LOCALMKTDATE", "Far leg settlement date for FX Swap."),
    FixFieldDefinition(8019, "FarLegBidAllInRate", "PRICE", "Far leg bid all-in rate. The complete bid exchange rate for the far leg of a swap (Spot + Far Leg Forward Points)."),
    FixFieldDefinition(8020, "FarLegOfferAllInRate", "PRICE", "Far leg offer all-in rate. The complete offer exchange rate for the far leg of a swap (Spot + Far Leg Forward Points)."),
    FixFieldDefinition(8021, "DealCurrency", "CURRENCY", "Deal currency. The currency in which the deal quantity is expressed (typically the base currency)."),
    FixFieldDefinition(8022, "ContraCurrency", "CURRENCY", "Contra currency. The other currency in the pair (typically the quote/terms currency)."),
    FixFieldDefinition(8023, "FarLegBidSize", "QTY", "Far leg bid size. The quantity available at the far leg bid rate."),
    FixFieldDefinition(8024, "FarLegOfferSize", "QTY", "Far leg offer size. The quantity available at the far leg offer rate."),

    # Smart Trade swap pricing tags (1000 range)
    FixFieldDefinition(1065, "BidSwapPoints", "PRICEOFFSET", "Total bid swap points. The combined forward points for the swap (far leg points minus near leg points) on the bid side."),
    FixFieldDefinition(1066, "OfferSwapPoints", "PRICEOFFSET", "Total offer swap points. The combined forward points for the swap (far leg points minus near leg points) on the offer side."),

    # Venue-specific market data tags (9000 range)
    FixFieldDefinition(9122, "VenueEntryTime", "UTCTIMEONLY", "Venue entry time. The time the market data entry was created at the venue/liquidity provider."),
    FixFieldDefinition(9123, "VenueEntryDate", "UTCDATEONLY", "Venue entry date. The date the market data entry was created at the venue."),

    # FX-specific tags (5700 range)
    FixFieldDefinition(5700, "FXCurrencyPair", "STRING", "FX currency pair. The pair being traded in standard format (e.g., EURUSD, USDJPY)."),
    FixFieldDefinition(5701, "BaseCurrency", "CURRENCY", "Base currency of the pair. The first currency in the pair (e.g., EUR in EUR/USD). Quantities are usually expressed in base currency."),
    FixFieldDefinition(5702, "QuoteCurrency", "CURRENCY", "Quote/Terms currency of the pair. The second currency in the pair (e.g., USD in EUR/USD). Price is units of quote currency per 1 base currency."),
    FixFieldDefinition(5703, "ValueDate", "LOCALMKTDATE", "Value date for FX trade. The date when currencies are exchanged (settlement date)."),
    FixFieldDefinition(5704, "FarValueDate", "LOCALMKTDATE", "Far leg value date for swap. Settlement date for the second leg of an FX Swap."),
    FixFieldDefinition(5705, "NearLegQty", "QTY", "Near leg quantity for swap. The notional amount for the first leg of an FX Swap."),
    FixFieldDefinition(5706, "FarLegQty", "QTY", "Far leg quantity for swap. The notional amount for the second leg of an FX Swap."),
    FixFieldDefinition(5707, "SwapPoints", "PRICEOFFSET", "Swap points. Forward points representing the interest rate differential between currencies."),
    FixFieldDefinition(5708, "AllInRate", "PRICE", "All-in rate including forward points. The complete forward exchange rate (Spot + Forward Points)."),
    FixFieldDefinition(5709, "NDFFixingDate", "LOCALMKTDATE", "NDF fixing date. The date when the NDF fixing rate is determined, usually 2 business days before settlement."),
    FixFieldDefinition(5710, "NDFFixingRate", "PRICE", "NDF fixing rate. The official exchange rate used to calculate NDF settlement amount, from an agreed fixing source."),
    FixFieldDefinition(5711, "NDFFixingSource", "STRING", "NDF fixing rate source. The official source for the NDF fixing rate (e.g., WMR, BFIX, Central Bank)."),
    FixFieldDefinition(5712, "TenorValue", "STRING", "Tenor value. Standardized tenor code for the trade (e.g., 1W, 1M, 3M, 1Y)."),
    FixFieldDefinition(5713, "FarTenorValue", "STRING", "Far leg tenor value for swap. Tenor code for the second leg of an FX Swap."),

    # Venue-specific tags (5800 range)
    FixFieldDefinition(5800, "VenueTradeID", "STRING", "Venue-specific trade ID. Unique trade identifier assigned by the execution venue."),
    FixFieldDefinition(5801, "VenueOrderID", "STRING", "Venue-specific order ID. Unique order identifier assigned by the execution venue."),
    FixFieldDefinition(5802, "VenueQuoteID", "STRING", "Venue-specific quote ID. Unique quote identifier assigned by the execution venue."),
    FixFieldDefinition(5803, "VenueName", "STRING", "Trading venue name. Name of the platform where the trade was executed."),
    FixFieldDefinition(5804, "VenueTimestamp", "UTCTIMESTAMP", "Venue timestamp. Timestamp assigned by the venue for the event."),

    # Counterparty tags (5900 range)
    FixFieldDefinition(5900, "CounterpartyID", "STRING", "Counterparty identifier. Unique ID of the trading counterparty (the other side of the trade)."),
    FixFieldDefinition(5901, "CounterpartyName", "STRING", "Counterparty name. Legal name of the trading counterparty."),
    FixFieldDefinition(5902, "CounterpartyLEI", "STRING", "Counterparty LEI code. Legal Entity Identifier of the counterparty, required for regulatory reporting."),

    # Regulatory tags (6000 range)
    FixFieldDefinition(6000, "TradeReportID", "STRING", "Trade report identifier. Unique ID for regulatory trade reporting."),
    FixFieldDefinition(6001, "RegulatoryReportType", "INT", "Regulatory report type. Indicates the type of regulatory report (e.g., EMIR, MiFID, Dodd-Frank)."),
    FixFieldDefinition(6002, "UTI", "STRING", "Unique Transaction Identifier. Globally unique ID for regulatory reporting under EMIR/MiFID."),
    FixFieldDefinition(6003, "USI", "STRING", "Unique Swap Identifier. Unique ID for swaps under Dodd-Frank reporting requirements."),

    # Options-specific tags (standard FIX but FX-relevant)
    FixFieldDefinition(201, "PutOrCall", "INT", "Put or call indicator. For FX Options, indicates whether option is a put or call on the base currency.", {
        "0": "Put", "1": "Call",
    }),
    FixFieldDefinition(202, "StrikePrice", "PRICE", "Strike price for option. The exchange rate at which the option can be exercised."),
    FixFieldDefinition(205, "MaturityDay", "DAYOFMONTH", "Maturity day of month. Day component of option expiry date."),
    FixFieldDefinition(200, "MaturityMonthYear", "MONTHYEAR", "Maturity month/year. Month and year of option expiry (format: YYYYMM)."),
    FixFieldDefinition(541, "MaturityDate", "LOCALMKTDATE", "Maturity date. Full expiry date for options or delivery date for futures."),
    FixFieldDefinition(223, "CouponRate", "PERCENTAGE", "Coupon rate. Interest rate for fixed income instruments."),
    FixFieldDefinition(231, "ContractMultiplier", "FLOAT", "Contract multiplier. Multiplier to convert price to contract value (e.g., lot size)."),
    FixFieldDefinition(206, "OptAttribute", "CHAR", "Option attribute. Additional option characteristic (e.g., American vs European exercise)."),
    FixFieldDefinition(207, "SecurityExchange", "EXCHANGE", "Security exchange. Exchange or market where the instrument trades (e.g., CME for FX Futures)."),

    # Additional standard FIX tags commonly used in FX
    FixFieldDefinition(423, "PriceType", "INT", "Price type. How the price is expressed (percentage, per unit, etc.).", {
        "1": "Percentage", "2": "PerUnit", "3": "FixedAmount",
        "4": "Discount", "5": "Premium", "6": "Spread",
        "7": "TEDPrice", "8": "TEDYield", "9": "Yield",
        "10": "FixedCabinetTradePrice", "11": "VariableCabinetTradePrice",
    }),
    FixFieldDefinition(424, "GTBookingInst", "INT", "GT booking instruction. How to book Good-Till orders (accumulate or separate)."),
    FixFieldDefinition(528, "OrderCapacity", "CHAR", "Order capacity. Indicates if order is for client (agency) or firm's own account (principal).", {
        "A": "Agency", "G": "Proprietary", "I": "Individual",
        "P": "Principal", "R": "RisklessPrincipal", "W": "AgentForOtherMember",
    }),
    FixFieldDefinition(529, "OrderRestrictions", "MULTIPLEVALUESTRING", "Order restrictions. Special handling instructions or restrictions on the order."),
    FixFieldDefinition(582, "CustOrderCapacity", "INT", "Customer order capacity. Capacity of the customer placing the order."),
    FixFieldDefinition(851, "LastLiquidityInd", "INT", "Last liquidity indicator. Indicates if the execution added or removed liquidity from the market.", {
        "1": "AddedLiquidity", "2": "RemovedLiquidity", "3": "LiquidityRoutedOut",
    }),
]
