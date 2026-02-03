"""FIX 4.4 standard tag definitions."""

from fxfixparser.core.field import FixFieldDefinition

FIX44_TAGS: list[FixFieldDefinition] = [
    # Header fields
    FixFieldDefinition(8, "BeginString", "STRING", "FIX protocol version identifier. Indicates which version of FIX protocol is being used (e.g., FIX.4.4)."),
    FixFieldDefinition(9, "BodyLength", "LENGTH", "Message body length in bytes. Used for message integrity validation, counting characters from tag 35 to the delimiter before tag 10."),
    FixFieldDefinition(35, "MsgType", "STRING", "Message type identifier. Defines the purpose and structure of the message (e.g., D=New Order, 8=Execution Report, R=Quote Request).", {
        "0": "Heartbeat", "1": "TestRequest", "2": "ResendRequest",
        "3": "Reject", "4": "SequenceReset", "5": "Logout",
        "6": "IOI", "7": "Advertisement", "8": "ExecutionReport",
        "9": "OrderCancelReject", "A": "Logon", "B": "News",
        "C": "Email", "D": "NewOrderSingle", "E": "NewOrderList",
        "F": "OrderCancelRequest", "G": "OrderCancelReplaceRequest",
        "H": "OrderStatusRequest", "J": "AllocationInstruction",
        "K": "ListCancelRequest", "L": "ListExecute", "M": "ListStatusRequest",
        "N": "ListStatus", "P": "AllocationInstructionAck",
        "Q": "DontKnowTrade", "R": "QuoteRequest", "S": "Quote",
        "T": "SettlementInstructions", "V": "MarketDataRequest",
        "W": "MarketDataSnapshotFullRefresh", "X": "MarketDataIncrementalRefresh",
        "Y": "MarketDataRequestReject", "Z": "QuoteCancel",
        "a": "QuoteStatusRequest", "b": "MassQuoteAck", "c": "SecurityDefinitionRequest",
        "d": "SecurityDefinition", "e": "SecurityStatusRequest", "f": "SecurityStatus",
        "g": "TradingSessionStatusRequest", "h": "TradingSessionStatus",
        "i": "MassQuote", "j": "BusinessMessageReject", "k": "BidRequest",
        "l": "BidResponse", "m": "ListStrikePrice", "n": "XMLMessage",
        "o": "RegistrationInstructions", "p": "RegistrationInstructionsResponse",
        "q": "OrderMassCancelRequest", "r": "OrderMassCancelReport",
        "s": "NewOrderCross", "t": "CrossOrderCancelReplaceRequest",
        "u": "CrossOrderCancelRequest", "v": "SecurityTypeRequest",
        "w": "SecurityTypes", "x": "SecurityListRequest", "y": "SecurityList",
        "z": "DerivativeSecurityListRequest",
    }),
    FixFieldDefinition(34, "MsgSeqNum", "SEQNUM", "Message sequence number. Sequential counter for messages in a FIX session, used for gap detection and message recovery."),
    FixFieldDefinition(49, "SenderCompID", "STRING", "Sender's company/system identifier. Identifies the firm or system sending the message (e.g., your trading system ID)."),
    FixFieldDefinition(56, "TargetCompID", "STRING", "Target's company/system identifier. Identifies the intended recipient of the message (e.g., broker, exchange, or venue)."),
    FixFieldDefinition(52, "SendingTime", "UTCTIMESTAMP", "Message sending timestamp in UTC. When the message was transmitted, used for latency measurement and audit trails."),
    FixFieldDefinition(50, "SenderSubID", "STRING", "Sender's sub-identifier. Additional granularity for sender (e.g., specific desk, trader, or application within the firm)."),
    FixFieldDefinition(57, "TargetSubID", "STRING", "Target's sub-identifier. Additional granularity for recipient (e.g., specific desk or service at the target firm)."),
    FixFieldDefinition(115, "OnBehalfOfCompID", "STRING", "On behalf of company ID. Used when a firm is sending orders on behalf of another firm (e.g., prime broker scenarios)."),
    FixFieldDefinition(116, "OnBehalfOfSubID", "STRING", "On behalf of sub-identifier. Additional detail for the firm being represented."),
    FixFieldDefinition(128, "DeliverToCompID", "STRING", "Deliver to company ID. Final destination when message is routed through intermediaries."),
    FixFieldDefinition(129, "DeliverToSubID", "STRING", "Deliver to sub-identifier. Additional detail for final destination."),
    FixFieldDefinition(43, "PossDupFlag", "BOOLEAN", "Possible duplicate flag. Indicates this message may be a duplicate of a previously sent message (Y=possible duplicate).", {"Y": "Yes", "N": "No"}),
    FixFieldDefinition(97, "PossResend", "BOOLEAN", "Possible resend flag. Indicates message may have been previously sent with different sequence number.", {"Y": "Yes", "N": "No"}),
    FixFieldDefinition(122, "OrigSendingTime", "UTCTIMESTAMP", "Original sending time. Timestamp of original message when PossDupFlag=Y, used for duplicate detection."),

    # Order/Trade fields
    FixFieldDefinition(1, "Account", "STRING", "Account identifier. The trading account to be used for this order, used for booking and P&L attribution."),
    FixFieldDefinition(11, "ClOrdID", "STRING", "Client order ID. Unique identifier assigned by the client/trader for this order, used to track order lifecycle."),
    FixFieldDefinition(37, "OrderID", "STRING", "Order ID assigned by broker/venue. Unique identifier assigned by the executing venue for order tracking."),
    FixFieldDefinition(17, "ExecID", "STRING", "Execution ID. Unique identifier for each execution report, used to track fills and order status changes."),
    FixFieldDefinition(19, "ExecRefID", "STRING", "Execution reference ID. Reference to a previous execution when correcting or canceling a fill."),
    FixFieldDefinition(20, "ExecTransType", "CHAR", "Execution transaction type. Indicates if this is a new execution, cancellation, or correction.", {
        "0": "New", "1": "Cancel", "2": "Correct", "3": "Status",
    }),
    FixFieldDefinition(39, "OrdStatus", "CHAR", "Order status. Current state of the order in its lifecycle (e.g., New, Filled, Canceled).", {
        "0": "New", "1": "PartiallyFilled", "2": "Filled", "3": "DoneForDay",
        "4": "Canceled", "5": "Replaced", "6": "PendingCancel",
        "7": "Stopped", "8": "Rejected", "9": "Suspended",
        "A": "PendingNew", "B": "Calculated", "C": "Expired",
        "D": "AcceptedForBidding", "E": "PendingReplace",
    }),
    FixFieldDefinition(40, "OrdType", "CHAR", "Order type. Specifies how the order should be executed (e.g., Market, Limit, Stop).", {
        "1": "Market", "2": "Limit", "3": "Stop", "4": "StopLimit",
        "5": "MarketOnClose", "6": "WithOrWithout", "7": "LimitOrBetter",
        "8": "LimitWithOrWithout", "9": "OnBasis", "A": "OnClose",
        "B": "LimitOnClose", "C": "ForexMarket", "D": "PreviouslyQuoted",
        "E": "PreviouslyIndicated", "F": "ForexLimit", "G": "ForexSwap",
        "H": "ForexPreviouslyQuoted", "I": "Funari", "J": "MarketIfTouched",
        "K": "MarketWithLeftover", "L": "PreviousFundValuationPoint",
        "M": "NextFundValuationPoint", "P": "Pegged",
    }),
    FixFieldDefinition(41, "OrigClOrdID", "STRING", "Original client order ID. Reference to original ClOrdID when amending or canceling an order."),
    FixFieldDefinition(54, "Side", "CHAR", "Side of order. Direction of the trade - whether client is buying or selling the base currency.", {
        "0": "Undisclosed", "1": "Buy", "2": "Sell", "3": "BuyMinus", "4": "SellPlus",
        "5": "SellShort", "6": "SellShortExempt", "7": "Undisclosed",
        "8": "Cross", "9": "CrossShort", "A": "CrossShortExempt",
        "B": "AsDefined", "C": "Opposite", "D": "Subscribe", "E": "Redeem",
        "F": "Lend", "G": "Borrow",
    }),
    FixFieldDefinition(55, "Symbol", "STRING", "Instrument symbol. The currency pair being traded (e.g., EUR/USD, USD/JPY). Base currency listed first."),
    FixFieldDefinition(48, "SecurityID", "STRING", "Security identifier. Alternative identifier for the instrument (e.g., ISIN, CUSIP)."),
    FixFieldDefinition(22, "SecurityIDSource", "STRING", "Security ID source. Identifies the type/source of SecurityID being used.", {
        "1": "CUSIP", "2": "SEDOL", "3": "QUIK", "4": "ISINNumber",
        "5": "RICCode", "6": "ISOCurrencyCode", "7": "ISOCountryCode",
        "8": "ExchangeSymbol", "9": "ConsolidatedTapeAssociation",
        "A": "BloombergSymbol", "B": "Wertpapier", "C": "Dutch",
        "D": "Valoren", "E": "Sicovam", "F": "Belgian", "G": "Common",
        "H": "ClearingHouse", "I": "ISDAFpML", "J": "OptionPriceReporting",
    }),
    FixFieldDefinition(65, "SymbolSfx", "STRING", "Symbol suffix. Additional information about the instrument variant."),
    FixFieldDefinition(167, "SecurityType", "STRING", "Security/product type. Identifies the type of FX instrument being traded.", {
        "FX": "ForeignExchange", "FXSPOT": "FXSpot", "FXFWD": "FXForward",
        "FXSWAP": "FXSwap", "FXNDF": "FXNonDeliverableForward",
    }),

    # Price/Quantity fields
    FixFieldDefinition(31, "LastPx", "PRICE", "Last executed price. The exchange rate at which the trade was executed."),
    FixFieldDefinition(32, "LastQty", "QTY", "Last executed quantity. The amount filled in this execution, in the deal currency."),
    FixFieldDefinition(38, "OrderQty", "QTY", "Order quantity. The total amount to trade, expressed in the Currency (tag 15) specified."),
    FixFieldDefinition(44, "Price", "PRICE", "Price per unit. Limit price for the order, or indicative price for quotes."),
    FixFieldDefinition(6, "AvgPx", "PRICE", "Average price. Volume-weighted average price of all fills for this order."),
    FixFieldDefinition(14, "CumQty", "QTY", "Cumulative quantity. Total quantity filled so far across all executions."),
    FixFieldDefinition(151, "LeavesQty", "QTY", "Leaves quantity. Remaining quantity open for further execution."),
    FixFieldDefinition(99, "StopPx", "PRICE", "Stop price. Trigger price for stop orders."),
    FixFieldDefinition(110, "MinQty", "QTY", "Minimum quantity. Minimum acceptable fill size."),
    FixFieldDefinition(111, "MaxFloor", "QTY", "Maximum floor. Maximum quantity to display in the market (iceberg orders)."),

    # Currency/Settlement fields
    FixFieldDefinition(15, "Currency", "CURRENCY", "Deal currency. The currency in which OrderQty is expressed (usually the base currency of the pair)."),
    FixFieldDefinition(120, "SettlCurrency", "CURRENCY", "Settlement currency. Currency for cash settlement (important for NDFs where only the difference is settled)."),
    FixFieldDefinition(119, "SettlCurrAmt", "AMT", "Settlement currency amount. The amount to be settled in SettlCurrency."),
    FixFieldDefinition(155, "SettlCurrFxRate", "FLOAT", "Settlement currency FX rate. Exchange rate used to convert between trade and settlement currencies."),
    FixFieldDefinition(156, "SettlCurrFxRateCalc", "CHAR", "Settlement FX rate calculation. How to apply the SettlCurrFxRate (multiply or divide).", {
        "M": "Multiply", "D": "Divide",
    }),
    FixFieldDefinition(63, "SettlType", "STRING", "Settlement type/tenor. When the trade settles - standard tenors or specific date. Determines value date.", {
        "0": "Regular", "1": "Cash", "2": "NextDay", "3": "TPlus2",
        "4": "TPlus3", "5": "TPlus4", "6": "Future", "7": "WhenIssued",
        "8": "SellersOption", "9": "TPlus5", "B": "BrokenDate", "C": "FXSpot",
        # Smart Trade / venue-specific string values
        "TOD": "Today", "TOM": "Tomorrow", "SPOT": "Spot", "SN": "SpotNext",
        "1W": "1Week", "2W": "2Weeks", "3W": "3Weeks",
        "1M": "1Month", "2M": "2Months", "3M": "3Months",
        "4M": "4Months", "5M": "5Months", "6M": "6Months",
        "9M": "9Months", "1Y": "1Year", "2Y": "2Years",
    }),
    FixFieldDefinition(64, "SettlDate", "LOCALMKTDATE", "Settlement date (value date). The date when currencies are exchanged. Format: YYYYMMDD."),
    FixFieldDefinition(193, "SettlDate2", "LOCALMKTDATE", "Settlement date for leg 2 (far leg). For FX Swaps, the value date of the second leg."),
    FixFieldDefinition(192, "OrderQty2", "QTY", "Order quantity for leg 2 (far leg). For FX Swaps, the notional amount of the second leg."),
    FixFieldDefinition(194, "LastSpotRate", "PRICE", "Spot rate. The current spot exchange rate, used as reference for forward calculations."),
    FixFieldDefinition(195, "LastForwardPoints", "PRICEOFFSET", "Forward points. The difference between forward rate and spot rate, expressed in pips. Added to spot for forward rate."),

    # Time fields
    FixFieldDefinition(60, "TransactTime", "UTCTIMESTAMP", "Transaction time. When the order/trade was created or executed, critical for trade reporting."),
    FixFieldDefinition(75, "TradeDate", "LOCALMKTDATE", "Trade date. The business date of the trade, may differ from TransactTime for after-hours trades."),
    FixFieldDefinition(59, "TimeInForce", "CHAR", "Time in force. How long the order remains active before expiring.", {
        "0": "Day", "1": "GoodTillCancel", "2": "AtTheOpening",
        "3": "ImmediateOrCancel", "4": "FillOrKill", "5": "GoodTillCrossing",
        "6": "GoodTillDate", "7": "AtTheClose",
    }),
    FixFieldDefinition(126, "ExpireTime", "UTCTIMESTAMP", "Expire time. Specific time when the order expires (for GTD orders)."),
    FixFieldDefinition(432, "ExpireDate", "LOCALMKTDATE", "Expire date. Date when the order expires."),

    # Execution fields
    FixFieldDefinition(150, "ExecType", "CHAR", "Execution type. Describes what triggered this execution report (new order, fill, cancel, etc.).", {
        "0": "New", "1": "PartialFill", "2": "Fill", "3": "DoneForDay",
        "4": "Canceled", "5": "Replace", "6": "PendingCancel",
        "7": "Stopped", "8": "Rejected", "9": "Suspended",
        "A": "PendingNew", "B": "Calculated", "C": "Expired",
        "D": "Restated", "E": "PendingReplace", "F": "Trade",
        "G": "TradeCorrect", "H": "TradeCancel", "I": "OrderStatus",
    }),
    FixFieldDefinition(103, "OrdRejReason", "INT", "Order reject reason. Code explaining why an order was rejected.", {
        "0": "BrokerOption", "1": "UnknownSymbol", "2": "ExchangeClosed",
        "3": "OrderExceedsLimit", "4": "TooLateToEnter",
        "5": "UnknownOrder", "6": "DuplicateOrder",
        "7": "DuplicateVerballyCommOrder", "8": "StaleOrder",
        "9": "TradeAlongRequired", "10": "InvalidInvestorID",
        "11": "UnsupportedOrderCharacteristic", "12": "SurveillanceOption",
        "13": "IncorrectQuantity", "14": "IncorrectAllocatedQuantity",
        "15": "UnknownAccount", "99": "Other",
    }),

    # Text/misc fields
    FixFieldDefinition(58, "Text", "STRING", "Free format text. Additional information or comments about the message."),
    FixFieldDefinition(354, "EncodedTextLen", "LENGTH", "Encoded text length. Length of EncodedText field when using non-ASCII characters."),
    FixFieldDefinition(355, "EncodedText", "DATA", "Encoded text. Text field with encoding for non-ASCII characters."),
    FixFieldDefinition(7, "BeginSeqNo", "SEQNUM", "Begin sequence number. Starting sequence number for message recovery requests."),
    FixFieldDefinition(16, "EndSeqNo", "SEQNUM", "End sequence number. Ending sequence number for message recovery requests."),
    FixFieldDefinition(36, "NewSeqNo", "SEQNUM", "New sequence number. New sequence number to use after a sequence reset."),
    FixFieldDefinition(45, "RefSeqNum", "SEQNUM", "Reference sequence number. Sequence number of message being referenced (e.g., in reject)."),
    FixFieldDefinition(98, "EncryptMethod", "INT", "Encryption method. Method used for message encryption.", {
        "0": "None", "1": "PKCS", "2": "DES", "3": "PKCSDES",
        "4": "PGPDES", "5": "PGPDESMD5", "6": "PEM",
    }),
    FixFieldDefinition(108, "HeartBtInt", "INT", "Heartbeat interval. Seconds between heartbeat messages to keep connection alive."),
    FixFieldDefinition(112, "TestReqID", "STRING", "Test request ID. Identifier for test request/heartbeat matching."),
    FixFieldDefinition(141, "ResetSeqNumFlag", "BOOLEAN", "Reset sequence number flag. Indicates sequence numbers should be reset on logon."),

    # Trailer
    FixFieldDefinition(10, "CheckSum", "STRING", "Message checksum. Three-character checksum for message integrity validation (sum of ASCII values mod 256)."),

    # Quote fields
    FixFieldDefinition(117, "QuoteID", "STRING", "Quote identifier. Unique ID assigned by the quoting party to identify this quote."),
    FixFieldDefinition(131, "QuoteReqID", "STRING", "Quote request identifier. Unique ID linking quote responses back to the original request."),
    FixFieldDefinition(132, "BidPx", "PRICE", "Bid price. Price at which the quoting party will buy the base currency (client sells)."),
    FixFieldDefinition(133, "OfferPx", "PRICE", "Offer/Ask price. Price at which the quoting party will sell the base currency (client buys)."),
    FixFieldDefinition(134, "BidSize", "QTY", "Bid size. Maximum quantity available at the bid price."),
    FixFieldDefinition(135, "OfferSize", "QTY", "Offer size. Maximum quantity available at the offer price."),
    FixFieldDefinition(188, "BidSpotRate", "PRICE", "Bid spot rate. Spot rate component of the bid price (for forwards/swaps)."),
    FixFieldDefinition(189, "BidForwardPoints", "PRICEOFFSET", "Bid forward points. Forward points to add to spot for the bid forward rate."),
    FixFieldDefinition(190, "OfferSpotRate", "PRICE", "Offer spot rate. Spot rate component of the offer price (for forwards/swaps)."),
    FixFieldDefinition(191, "OfferForwardPoints", "PRICEOFFSET", "Offer forward points. Forward points to add to spot for the offer forward rate."),

    # FX Swap second leg quote fields
    FixFieldDefinition(642, "SettlBidForwardPoints2", "PRICEOFFSET", "Far leg bid forward points (Leg 2). Forward points to add to spot for the far leg bid rate in FX Swaps."),
    FixFieldDefinition(643, "SettlOfferForwardPoints2", "PRICEOFFSET", "Far leg offer forward points (Leg 2). Forward points to add to spot for the far leg offer rate in FX Swaps."),
    FixFieldDefinition(645, "MidPx", "PRICE", "Mid price. The middle price between bid and offer."),
    FixFieldDefinition(646, "MidYield", "PERCENTAGE", "Mid yield. The middle yield between bid and offer yields."),

    # Parties
    FixFieldDefinition(453, "NoPartyIDs", "NUMINGROUP", "Number of party IDs. Count of party identification entries that follow."),
    FixFieldDefinition(448, "PartyID", "STRING", "Party identifier. Identifier for a party involved in the trade (trader, firm, account, etc.)."),
    FixFieldDefinition(447, "PartyIDSource", "CHAR", "Party ID source. Identifies the type/format of the PartyID.", {
        "B": "BIC", "C": "GeneralIdentifier", "D": "Proprietary",
        "E": "ISOCountryCode", "F": "SettlementEntityLocation",
        "G": "MIC", "H": "CSDParticipant", "I": "DirectedBroker",
    }),
    FixFieldDefinition(452, "PartyRole", "INT", "Party role. The role/function of this party in the trade.", {
        "1": "ExecutingFirm", "2": "BrokerOfCredit", "3": "ClientID",
        "4": "ClearingFirm", "5": "InvestorID", "6": "IntroducingFirm",
        "7": "EnteringFirm", "8": "Locate", "9": "FundManager",
        "10": "SettlementLocation", "11": "OrderOriginationTrader",
        "12": "ExecutingTrader", "13": "OrderOriginationFirm",
        "14": "GiveupClearingFirm", "15": "CorrespondantClearingFirm",
        "16": "ExecutingSystem", "17": "ContraFirm", "18": "ContraClearingFirm",
        "19": "SponsoringFirm", "20": "UnderlyingContraFirm",
        "21": "ClearingOrganization", "22": "Exchange",
        "24": "CustomerAccount", "36": "Trader", "37": "TraderMnemonic",
        "66": "AllocatingEntity", "82": "PositionAccount",
        "500": "AlgoClient",
    }),

    # Quote Request fields
    FixFieldDefinition(146, "NoRelatedSym", "NUMINGROUP", "Number of related symbols. Count of instruments in a quote request or market data request."),
    FixFieldDefinition(303, "QuoteRequestType", "INT", "Quote request type. Indicates if quote is manually or automatically generated.", {
        "1": "Manual", "2": "Automatic",
    }),
    FixFieldDefinition(537, "QuoteType", "INT", "Quote type. Indicates whether quote is indicative or tradeable.", {
        "0": "Indicative", "1": "Tradeable", "2": "RestrictedTradeable", "3": "Counter",
    }),
    FixFieldDefinition(692, "QuotePriceType", "INT", "Quote price type. How the quote price is expressed."),
    FixFieldDefinition(301, "QuoteResponseLevel", "INT", "Quote response level. Level of acknowledgement requested for quotes.", {
        "0": "NoAcknowledgement", "1": "AckNegativeOnly", "2": "AckEach",
    }),

    # Quote Acknowledgement fields
    FixFieldDefinition(297, "QuoteAckStatus", "INT", "Quote acknowledgement status. Indicates whether the quote was accepted, rejected, or other status.", {
        "0": "Accepted", "1": "CancelForSymbol", "2": "CanceledForSecurityType",
        "3": "CanceledForUnderlying", "4": "CanceledAll", "5": "Rejected",
        "6": "RemovedFromMarket", "7": "Expired", "8": "Query",
        "9": "QuoteNotFound", "10": "Pending", "11": "Pass", "12": "LockedMarketWarning",
        "13": "CrossMarketWarning", "14": "CanceledDueToLockMarket",
        "15": "CanceledDueToCrossMarket",
    }),
    FixFieldDefinition(300, "QuoteRejectReason", "INT", "Quote reject reason. Reason quote was rejected.", {
        "1": "UnknownSymbol", "2": "Exchange", "3": "QuoteRequestExceedsLimit",
        "4": "TooLateToEnter", "5": "UnknownQuote", "6": "DuplicateQuote",
        "7": "InvalidBidAskSpread", "8": "InvalidPrice", "9": "NotAuthorizedToQuoteSecurity",
        "99": "Other",
    }),
    FixFieldDefinition(658, "QuoteRequestRejectReason", "INT", "Quote request reject reason. Reason the quote request was rejected.", {
        "1": "UnknownSymbol", "2": "Exchange", "3": "QuoteRequestExceedsLimit",
        "4": "TooLateToEnter", "5": "InvalidPrice", "6": "NotAuthorizedToRequestQuote",
        "7": "NoMatchForInquiry", "8": "NoMarketForInstrument", "9": "NoInventory",
        "10": "Pass", "11": "InsufficientCredit",
        "99": "Other",
    }),
    FixFieldDefinition(694, "QuoteRespID", "STRING", "Quote response identifier. Unique ID for the quote response."),
    FixFieldDefinition(695, "QuoteRespType", "INT", "Quote response type. Type of quote response.", {
        "1": "HitLift", "2": "Counter", "3": "Expired", "4": "Cover", "5": "DoneAway",
        "6": "Pass",
    }),

    # Market Data fields
    FixFieldDefinition(262, "MDReqID", "STRING", "Market data request identifier. Unique ID for the market data request, used to match responses."),
    FixFieldDefinition(263, "SubscriptionRequestType", "CHAR", "Subscription request type. Type of market data subscription.", {
        "0": "Snapshot", "1": "SnapshotPlusUpdates", "2": "DisablePreviousSnapshot",
    }),
    FixFieldDefinition(264, "MarketDepth", "INT", "Market depth. Depth of market data requested (0=full book, 1=top of book, N=N levels)."),
    FixFieldDefinition(265, "MDUpdateType", "INT", "Market data update type. How updates are sent.", {
        "0": "FullRefresh", "1": "IncrementalRefresh",
    }),
    FixFieldDefinition(266, "AggregatedBook", "BOOLEAN", "Aggregated book. Whether market data is aggregated.", {"Y": "Yes", "N": "No"}),
    FixFieldDefinition(267, "NoMDEntryTypes", "NUMINGROUP", "Number of market data entry types requested."),
    FixFieldDefinition(268, "NoMDEntries", "NUMINGROUP", "Number of market data entries. Count of price/size entries in the message."),
    FixFieldDefinition(269, "MDEntryType", "CHAR", "Market data entry type. Type of market data entry (bid, offer, trade, etc.).", {
        "0": "Bid", "1": "Offer", "2": "Trade", "3": "IndexValue", "4": "OpeningPrice",
        "5": "ClosingPrice", "6": "SettlementPrice", "7": "TradingSessionHighPrice",
        "8": "TradingSessionLowPrice", "9": "TradingSessionVWAPPrice", "A": "Imbalance",
        "B": "TradeVolume", "C": "OpenInterest",
    }),
    FixFieldDefinition(270, "MDEntryPx", "PRICE", "Market data entry price. Price for this market data entry (bid price, offer price, trade price, etc.)."),
    FixFieldDefinition(271, "MDEntrySize", "QTY", "Market data entry size. Quantity available at this price level."),
    FixFieldDefinition(272, "MDEntryDate", "UTCDATEONLY", "Market data entry date. Date of this market data entry."),
    FixFieldDefinition(273, "MDEntryTime", "UTCTIMEONLY", "Market data entry time. Time of this market data entry."),
    FixFieldDefinition(274, "TickDirection", "CHAR", "Tick direction. Direction of price change.", {
        "0": "PlusTick", "1": "ZeroPlusTick", "2": "MinusTick", "3": "ZeroMinusTick",
    }),
    FixFieldDefinition(275, "MDMkt", "EXCHANGE", "Market data market. Market/exchange for this entry."),
    FixFieldDefinition(276, "QuoteCondition", "MULTIPLEVALUESTRING", "Quote condition. Condition of the quote.", {
        "A": "Open/Active", "B": "Closed/Inactive", "C": "ExchangeBest", "D": "ConsolidatedBest",
        "E": "Locked", "F": "Crossed", "G": "Depth", "H": "FastTrading", "I": "NonFirm",
    }),
    FixFieldDefinition(277, "TradeCondition", "MULTIPLEVALUESTRING", "Trade condition. Condition of the trade."),
    FixFieldDefinition(278, "MDEntryID", "STRING", "Market data entry identifier. Unique ID for this market data entry, used for updates/deletes."),
    FixFieldDefinition(279, "MDUpdateAction", "CHAR", "Market data update action. Action for incremental refresh.", {
        "0": "New", "1": "Change", "2": "Delete", "3": "DeleteThru", "4": "DeleteFrom",
    }),
    FixFieldDefinition(280, "MDEntryRefID", "STRING", "Market data entry reference ID. Reference to another entry (e.g., for delete actions)."),
    FixFieldDefinition(281, "MDReqRejReason", "CHAR", "Market data request reject reason.", {
        "0": "UnknownSymbol", "1": "DuplicateMDReqID", "2": "InsufficientBandwidth",
        "3": "InsufficientPermissions", "4": "UnsupportedSubscriptionRequestType",
        "5": "UnsupportedMarketDepth", "6": "UnsupportedMDUpdateType",
        "7": "UnsupportedAggregatedBook", "8": "UnsupportedMDEntryType",
        "9": "UnsupportedTradingSessionID", "A": "UnsupportedScope", "B": "UnsupportedOpenCloseSettleFlag",
        "C": "UnsupportedMDImplicitDelete",
    }),
    FixFieldDefinition(282, "MDEntryOriginator", "STRING", "Market data entry originator. Source/originator of this market data entry (e.g., liquidity provider ID)."),
    FixFieldDefinition(283, "LocationID", "STRING", "Location identifier. Geographic location for the entry."),
    FixFieldDefinition(284, "DeskID", "STRING", "Desk identifier. Trading desk identifier."),
    FixFieldDefinition(286, "OpenCloseSettlFlag", "MULTIPLEVALUESTRING", "Open/close/settle flag.", {
        "0": "DailyOpen", "1": "SessionOpen", "2": "DeliverySettlementEntry",
        "3": "ExpectedEntry", "4": "EntryFromPreviousBusinessDay", "5": "TheoreticalPriceValue",
    }),
    FixFieldDefinition(290, "MDEntryPositionNo", "INT", "Market data entry position number. Position in the book (1=best, 2=second best, etc.)."),
    FixFieldDefinition(291, "FinancialStatus", "MULTIPLEVALUESTRING", "Financial status of the security."),
    FixFieldDefinition(292, "CorporateAction", "MULTIPLEVALUESTRING", "Corporate action indicator."),
]
